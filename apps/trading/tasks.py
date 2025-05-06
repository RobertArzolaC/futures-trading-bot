import logging
from datetime import timedelta
from decimal import Decimal

from binance.client import Client
from binance.exceptions import BinanceAPIException
from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.trading import choices, models
from apps.trading.strategies import (
    _market_fetcher,
    adxt_trending,
    bollinger_reversal,
    ema9_21,
    fibonacci_retracement,
    ichimoku,
    macd_divergence,
    pivot_points,
    rsi_ma_crossover,
    triple_ema,
    volume_profile,
)

# Configurar logging
logger = logging.getLogger(__name__)

User = get_user_model()


@shared_task
def process_signal(signal_id):
    """Procesa una señal recibida y determina si se deben tomar acciones"""
    try:
        signal = models.Signal.objects.get(id=signal_id)

        if signal.processed:
            return f"Signal {signal_id} already processed"

        logger.info(f"Processing signal: {signal}")

        # Marcar como procesada
        signal.processed = True
        signal.save()

        # Verificar si hay 5 señales consecutivas del mismo tipo
        # con diferentes estrategias
        check_consecutive_signals.delay(signal.ticker)

        return f"Signal {signal_id} processed successfully"

    except models.Signal.DoesNotExist:
        logger.error(f"Signal {signal_id} not found")
        return f"Signal {signal_id} not found"
    except Exception as e:
        logger.error(f"Error processing signal {signal_id}: {str(e)}")
        return f"Error processing signal {signal_id}: {str(e)}"


@shared_task
def check_consecutive_signals(ticker):
    """Verifica si hay 5 señales consecutivas del mismo tipo con estrategias diferentes"""
    try:
        # Obtener señales en los últimos 60 minutos
        one_hour_ago = timezone.now() - timedelta(minutes=60)
        recent_signals = models.Signal.objects.filter(
            ticker=ticker, timestamp__gte=one_hour_ago
        ).order_by("-created")

        if recent_signals.count() < 5:
            return "Not enough signals to check"

        # Detectar secuencias de buy o sell consecutivas
        buy_signals = []
        sell_signals = []

        for signal in recent_signals:
            if signal.signal_type == choices.OrderSide.BUY:
                buy_signals.append(signal)
                sell_signals = []
            elif signal.signal_type == choices.OrderSide.SELL:
                sell_signals.append(signal)
                buy_signals = []

            # Verificar si tenemos 5 señales del mismo tipo
            if len(buy_signals) >= 5:
                # Verificar que sean estrategias diferentes
                strategies = set([s.strategy for s in buy_signals[:5]])
                if len(strategies) == 5:
                    # Crear grupo de señales
                    signal_group = models.SignalGroup.objects.create(
                        direction=choices.OrderSide.BUY
                    )
                    signal_group.signals.add(*buy_signals[:5])

                    # Notificar a todos los usuarios con este símbolo configurado
                    users = User.objects.filter(trading_settings__symbol=ticker)
                    for user in users:
                        handle_signal_confirmation.delay(
                            user_id=user.id,
                            signal_group_id=signal_group.id,
                            direction=choices.OrderSide.BUY,
                        )

                    return f"Buy signal group created: {signal_group.id}"

            elif len(sell_signals) >= 5:
                # Verificar que sean estrategias diferentes
                strategies = set([s.strategy for s in sell_signals[:5]])
                if len(strategies) == 5:
                    # Crear grupo de señales
                    signal_group = models.SignalGroup.objects.create(
                        direction=choices.OrderSide.SELL
                    )
                    signal_group.signals.add(*sell_signals[:5])

                    # Notificar a todos los usuarios con este símbolo configurado
                    users = User.objects.filter(trading_settings__symbol=ticker)
                    for user in users:
                        handle_signal_confirmation.delay(
                            user_id=user.id,
                            signal_group_id=signal_group.id,
                            direction=choices.OrderSide.SELL,
                        )

                    return f"Sell signal group created: {signal_group.id}"

        return "No consecutive signal patterns found"

    except Exception as e:
        logger.error(
            f"Error checking consecutive signals for {ticker}: {str(e)}"
        )
        return f"Error checking consecutive signals: {str(e)}"


@shared_task
def handle_signal_confirmation(user_id, signal_group_id, direction):
    """Maneja la confirmación de un grupo de señales para un usuario"""
    try:
        logger.info(
            f"Handling signal confirmation for user {user_id}, group {signal_group_id}, direction {direction}"
        )
        user = User.objects.get(id=user_id)
        signal_group = models.SignalGroup.objects.get(id=signal_group_id)

        # Obtener el estado del bot para el usuario
        bot, _ = models.Bot.objects.get_or_create(user=user)

        # Verificar si el bot está activo
        if bot.status == choices.BotStatus.IDLE:
            logger.info(f"Bot for user {user.email} is idle, ignoring signals")
            return f"Bot is idle for user {user_id}, signals ignored"

        # Verificar si hay una operación abierta
        if bot.current_operation:
            current_op = bot.current_operation
            current_direction = (
                choices.OrderSide.BUY
                if current_op.direction == choices.OperationDirection.LONG
                else choices.OrderSide.SELL
            )

            # Si la dirección es contraria, cerrar posición actual y abrir nueva
            if current_direction != direction:
                logger.info(
                    f"Closing current {current_direction} position to open {direction}"
                )
                close_position.delay(operation_id=current_op.id)

                # Abrir nueva posición después de un breve delay
                open_position_from_signals.apply_async(
                    args=[user_id, signal_group.id], countdown=5
                )
            else:
                logger.info(
                    f"Already in a {direction} position, ignoring signals"
                )
        else:
            # No hay operación activa, abrir nueva
            open_position_from_signals.delay(user_id, signal_group.id)

        return f"Signal confirmation handled for user {user_id}"

    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return f"User {user_id} not found"
    except models.SignalGroup.DoesNotExist:
        logger.error(f"Signal group {signal_group_id} not found")
        return f"Signal group {signal_group_id} not found"
    except Exception as e:
        logger.error(
            f"Error handling signal confirmation for user {user_id}: {str(e)}"
        )
        return f"Error handling signal confirmation: {str(e)}"


@shared_task
def open_position_from_signals(user_id, signal_group_id):
    """Abre una posición basada en un grupo de señales"""
    try:
        user = User.objects.get(id=user_id)
        signal_group = models.SignalGroup.objects.get(id=signal_group_id)

        # Obtener la configuración del usuario
        settings = models.TradingSettings.objects.get(user=user)

        # Determinar dirección de la operación
        direction = (
            choices.OperationDirection.LONG
            if signal_group.direction == choices.OrderSide.BUY
            else choices.OperationDirection.SHORT
        )

        # Obtener la primera señal para el símbolo y precio
        first_signal = signal_group.signals.all().order_by("timestamp").first()
        symbol = first_signal.ticker

        # Abrir la posición
        return open_position.delay(
            user_id=user_id,
            symbol=symbol,
            direction=direction,
            investment_percentage=settings.investment_percentage,
            leverage=settings.leverage,
            take_profit=settings.take_profit,
            stop_loss=settings.stop_loss,
            signal_group_id=signal_group_id,
        )

    except Exception as e:
        logger.error(
            f"Error opening position from signals for user {user_id}: {str(e)}"
        )
        return f"Error opening position from signals: {str(e)}"


@shared_task
def open_position(
    user_id,
    symbol,
    direction,
    investment_percentage,
    leverage,
    take_profit,
    stop_loss,
    signal_group_id=None,
):
    """Abre una posición en Binance"""
    try:
        user = User.objects.get(id=user_id)
        settings = models.TradingSettings.objects.get(user=user)

        # Verificar credenciales de Binance
        if not settings.api_key_token or not settings.api_secret_token:
            logger.error(
                f"Binance API credentials not configured for user {user.email}"
            )
            return "Binance API credentials not configured"

        # Inicializar cliente Binance
        client = Client(settings.api_key_token, settings.api_secret_token)

        # Configurar apalancamiento
        client.futures_change_leverage(symbol=symbol, leverage=leverage)

        # Obtener información de la cuenta
        account = client.futures_account()
        available_balance = float(account["availableBalance"])
        logger.info(
            f"Available balance for user {user.email}: {available_balance}"
        )

        # Calcular tamaño de la posición
        position_size = available_balance * investment_percentage / 100

        # Obtener precio actual
        ticker = client.futures_symbol_ticker(symbol=symbol)
        current_price = float(ticker["price"])

        # Calcular cantidad (respetando la precisión de Binance)
        symbol_info = client.futures_exchange_info()
        quantity_precision = 0
        for s in symbol_info["symbols"]:
            if s["symbol"] == symbol:
                quantity_precision = s["quantityPrecision"]
                break

        quantity = position_size / current_price
        quantity = round(quantity, quantity_precision)

        # Abrir posición
        side = (
            choices.OrderSide.BUY
            if direction == choices.OperationDirection.LONG
            else choices.OrderSide.SELL
        )
        logger.info(
            f"Opening position for user {user.email}: {symbol} {side} {quantity}"
        )
        # client.futures_create_order(
        #     symbol=symbol,
        #     side=side,
        #     type=choices.OrderType.MARKET,
        #     quantity=quantity,
        # )

        # Crear registro de operación
        operation = models.Operation.objects.create(
            user=user,
            symbol=symbol,
            direction=direction,
            status=choices.OperationStatus.OPEN,
            entry_price=Decimal(str(current_price)),
            quantity=Decimal(str(quantity)),
            leverage=leverage,
            investment=Decimal(str(position_size)),
            take_profit=take_profit,
            stop_loss=stop_loss,
        )

        # Actualizar estado del bot
        bot_status, _ = models.Bot.objects.get_or_create(user=user)
        bot_status.status = choices.BotStatus.OPERATING
        bot_status.current_operation = operation
        bot_status.save()

        # Si viene de un grupo de señales, asociarlo
        if signal_group_id:
            try:
                signal_group = models.SignalGroup.objects.get(
                    id=signal_group_id
                )
                signal_group.operation = operation
                signal_group.save()
            except models.SignalGroup.DoesNotExist:
                pass

        logger.info(
            f"Position opened for user {user.email}: {symbol} {direction}"
        )
        return f"Position opened: {operation.id}"

    except BinanceAPIException as e:
        logger.error(f"Binance API error: {e}")
        return f"Binance API error: {e}"
    except Exception as e:
        logger.error(f"Error opening position for user {user_id}: {str(e)}")
        return f"Error opening position: {str(e)}"


@shared_task
def close_position(operation_id):
    """Cierra una posición existente"""
    try:
        operation = models.Operation.objects.get(
            id=operation_id, status=choices.OperationStatus.OPEN
        )
        user = operation.user
        settings = models.TradingSettings.objects.get(user=user)

        # Verificar credenciales de Binance
        if not settings.api_key_token or not settings.api_secret_token:
            logger.error(
                f"Binance API credentials not configured for user {user.email}"
            )
            return "Binance API credentials not configured"

        # Inicializar cliente Binance
        client = Client(settings.api_key_token, settings.api_secret_token)

        # Obtener precio actual
        ticker = client.futures_symbol_ticker(symbol=operation.symbol)
        current_price = float(ticker["price"])

        # Cerrar posición
        side = (
            choices.OrderSide.SELL
            if operation.direction == choices.OperationDirection.LONG
            else choices.OrderSide.BUY
        )
        logger.info(
            f"Closing position for user {user.email}: {operation.symbol} {side}"
        )
        # client.futures_create_order(
        #     symbol=operation.symbol,
        #     side=side,
        #     type=choices.OrderType.MARKET,
        #     quantity=float(operation.quantity),
        # )

        # Calcular resultados
        entry_price = float(operation.entry_price)
        price_change = ((current_price - entry_price) / entry_price) * 100
        if operation.direction == choices.OperationDirection.SHORT:
            price_change = -price_change

        profit = price_change * operation.leverage
        profit_usd = float(operation.investment) * (profit / 100)

        # Actualizar operación
        operation.status = choices.OperationStatus.CLOSED
        operation.exit_price = Decimal(str(current_price))
        operation.profit_loss = Decimal(str(profit_usd))
        operation.profit_loss_percentage = Decimal(str(profit))
        operation.closed_at = timezone.now()
        operation.save()

        # Actualizar estado del bot
        bot_status = models.Bot.objects.get(user=user)
        if (
            bot_status.current_operation
            and bot_status.current_operation.id == operation.id
        ):
            bot_status.current_operation = None
            bot_status.status = choices.BotStatus.LISTENING
            bot_status.save()

        logger.info(
            f"Position closed for user {user.email}: {operation.symbol}"
        )
        return f"Position closed: {operation.id}"

    except models.Operation.DoesNotExist:
        logger.error(f"Operation {operation_id} not found or already closed")
        return f"Operation {operation_id} not found or already closed"
    except Exception as e:
        logger.error(f"Error closing position {operation_id}: {str(e)}")
        return f"Error closing position: {str(e)}"


@shared_task
def check_positions_status():
    """Verifica el estado de todas las operaciones abiertas"""
    open_operations = models.Operation.objects.filter(
        status=choices.OperationStatus.OPEN
    )

    for operation in open_operations:
        try:
            user = operation.user
            settings = models.TradingSettings.objects.get(user=user)

            # Verificar credenciales de Binance
            if not settings.api_key_token or not settings.api_secret_token:
                continue

            # Inicializar cliente Binance
            client = Client(settings.api_key_token, settings.api_secret_token)

            # Obtener precio actual
            ticker = client.futures_symbol_ticker(symbol=operation.symbol)
            current_price = float(ticker["price"])

            # Calcular ganancia/pérdida actual
            entry_price = float(operation.entry_price)
            price_change = ((current_price - entry_price) / entry_price) * 100
            if operation.direction == choices.OperationDirection.SHORT:
                price_change = -price_change

            profit = price_change * operation.leverage

            # Verificar si se alcanzó el take profit o stop loss
            if profit >= operation.take_profit:
                logger.info(
                    f"Take profit reached for operation {operation.id}: {profit:.2f}%"
                )
                close_position.delay(operation_id=operation.id)
            elif profit <= -operation.stop_loss:
                logger.info(
                    f"Stop loss reached for operation {operation.id}: {profit:.2f}%"
                )
                close_position.delay(operation_id=operation.id)

        except Exception as e:
            logger.error(f"Error checking position {operation.id}: {str(e)}")


@shared_task
def process_pending_signals():
    """Procesa señales pendientes"""
    unprocessed_signals = models.Signal.objects.filter(processed=False)

    for signal in unprocessed_signals:
        process_signal.delay(signal_id=signal.id)


@shared_task
def start_bot(user_id):
    """Inicia el bot para un usuario"""
    try:
        user = User.objects.get(id=user_id)
        bot, _ = models.Bot.objects.get_or_create(user=user)

        bot.status = choices.BotStatus.LISTENING
        bot.save()

        logger.info(f"Bot started for user {user.email}")
        return f"Bot started for user {user_id}"
    except Exception as e:
        logger.error(f"Error starting bot for user {user_id}: {str(e)}")
        return f"Error starting bot: {str(e)}"


@shared_task
def stop_bot(user_id):
    """Detiene el bot para un usuario"""
    try:
        user = User.objects.get(id=user_id)
        bot, _ = models.models.Bot.objects.get_or_create(user=user)

        bot.status = choices.BotStatus.IDLE
        bot.save()

        logger.info(f"Bot stopped for user {user.email}")

        return f"Bot stopped for user {user_id}"
    except Exception as e:
        logger.error(f"Error stopping bot for user {user_id}: {str(e)}")
        return f"Error stopping bot: {str(e)}"


@shared_task
def restart_bot(user_id):
    """Reinicia el bot para un usuario"""
    try:
        stop_bot(user_id)
        start_bot(user_id)
        return f"Bot restarted for user {user_id}"
    except Exception as e:
        logger.error(f"Error restarting bot for user {user_id}: {str(e)}")
        return f"Error restarting bot: {str(e)}"


@shared_task
def run_strategies():
    """Ejecuta las estrategias de trading para todos los usuarios"""
    symbol = "BTC/USDT"
    timeframe = "15m"
    fetcher = _market_fetcher.MarketDataFetcher(symbol, timeframe)
    data = fetcher.fetch()

    strategies_list = [
        rsi_ma_crossover.RSIMACrossoverStrategy,
        adxt_trending.ADXTrendStrategy,
        bollinger_reversal.BollingerReversalStrategy,
        ema9_21.EMA921Strategy,
        triple_ema.TripleEMAStrategy,
        fibonacci_retracement.FibonacciRetracementStrategy,
        ichimoku.IchimokuStrategy,
        macd_divergence.MACDDivergenceStrategy,
        pivot_points.PivotPointsStrategy,
        volume_profile.VolumeProfileStrategy,
    ]

    for strategy_class in strategies_list:
        strategy = strategy_class(data, symbol, timeframe)
        signal_data = strategy.generate_signal()
        signal = models.Signal.objects.create(
            ticker=symbol,
            signal_type=signal_data["signal"],
            timeframe=timeframe,
            strategy=strategy.__class__.__name__,
            price_close=signal_data["price_close"],
        )

        process_signal.delay(signal_id=signal.id)
