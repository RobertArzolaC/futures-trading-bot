import logging
from datetime import timedelta
from decimal import Decimal

from binance.client import Client
from binance.exceptions import BinanceAPIException
from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.trading import models, utils

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

        # Obtener señales en los últimos 60 minutos para el mismo símbolo
        one_hour_ago = timezone.now() - timedelta(minutes=60)
        recent_signals = models.Signal.objects.filter(
            ticker=signal.ticker, timestamp__gte=one_hour_ago
        ).order_by("timestamp")

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
        ).order_by("timestamp")

        if recent_signals.count() < 5:
            return "Not enough signals to check"

        # Detectar secuencias de buy o sell consecutivas
        buy_signals = []
        sell_signals = []

        for signal in recent_signals:
            if signal.signal_type == "buy":
                buy_signals.append(signal)
                sell_signals = []  # Reiniciar secuencia de sell
            else:  # sell
                sell_signals.append(signal)
                buy_signals = []  # Reiniciar secuencia de buy

            # Verificar si tenemos 5 señales del mismo tipo
            if len(buy_signals) >= 5:
                # Verificar que sean estrategias diferentes
                strategies = set([s.strategy for s in buy_signals[:5]])
                if len(strategies) == 5:
                    # Crear grupo de señales
                    signal_group = models.SignalGroup.objects.create(
                        direction="buy"
                    )
                    signal_group.signals.add(*buy_signals[:5])

                    # Notificar a todos los usuarios con este símbolo configurado
                    users = User.objects.filter(trading_settings__symbol=ticker)
                    for user in users:
                        handle_signal_confirmation.delay(
                            user_id=user.id,
                            signal_group_id=signal_group.id,
                            direction="buy",
                        )

                    return f"Buy signal group created: {signal_group.id}"

            elif len(sell_signals) >= 5:
                # Verificar que sean estrategias diferentes
                strategies = set([s.strategy for s in sell_signals[:5]])
                if len(strategies) == 5:
                    # Crear grupo de señales
                    signal_group = models.SignalGroup.objects.create(
                        direction="sell"
                    )
                    signal_group.signals.add(*sell_signals[:5])

                    # Notificar a todos los usuarios con este símbolo configurado
                    users = User.objects.filter(trading_settings__symbol=ticker)
                    for user in users:
                        handle_signal_confirmation.delay(
                            user_id=user.id,
                            signal_group_id=signal_group.id,
                            direction="sell",
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
        user = User.objects.get(id=user_id)
        signal_group = models.SignalGroup.objects.get(id=signal_group_id)

        # Obtener el estado del bot para el usuario
        bot_status, created = models.models.BotStatus.objects.get_or_create(
            user=user
        )

        # Verificar si el bot está activo
        if bot_status.status == "idle":
            logger.info(
                f"Bot for user {user.username} is idle, ignoring signals"
            )
            return f"Bot is idle for user {user_id}, signals ignored"

        # Verificar si hay una operación abierta
        if bot_status.current_operation:
            current_op = bot_status.current_operation
            current_direction = (
                "buy" if current_op.direction == "long" else "sell"
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
        direction = "long" if signal_group.direction == "buy" else "short"

        # Obtener la primera señal para el símbolo y precio
        first_signal = signal_group.signals.all().order_by("timestamp").first()
        symbol = first_signal.ticker

        # Abrir la posición
        return open_position(
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
        if not settings.api_key or not settings.api_secret:
            logger.error(
                f"Binance API credentials not configured for user {user.username}"
            )
            return "Binance API credentials not configured"

        # Inicializar cliente Binance
        client = Client(settings.api_key, settings.api_secret)

        # Configurar apalancamiento
        client.futures_change_leverage(symbol=symbol, leverage=leverage)

        # Obtener información de la cuenta
        account = client.futures_account()
        available_balance = float(account["availableBalance"])

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
        side = "BUY" if direction == "long" else "SELL"
        order = client.futures_create_order(
            symbol=symbol, side=side, type="MARKET", quantity=quantity
        )

        # Crear registro de operación
        operation = models.Operation.objects.create(
            user=user,
            symbol=symbol,
            direction=direction,
            status="open",
            entry_price=Decimal(str(current_price)),
            quantity=Decimal(str(quantity)),
            leverage=leverage,
            investment=Decimal(str(position_size)),
            take_profit=take_profit,
            stop_loss=stop_loss,
        )

        # Actualizar estado del bot
        bot_status, _ = models.BotStatus.objects.get_or_create(user=user)
        bot_status.status = "operating"
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

        # Enviar notificación de Telegram si está configurado
        if settings.telegram_bot_token and settings.telegram_chat_id:
            send_telegram_notification.delay(
                user_id=user_id,
                message=f"Position opened:\n\n{utils.format_operation_info(operation)}",
            )

        logger.info(
            f"Position opened for user {user.username}: {symbol} {direction}"
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
        operation = models.Operation.objects.get(id=operation_id, status="open")
        user = operation.user
        settings = models.TradingSettings.objects.get(user=user)

        # Verificar credenciales de Binance
        if not settings.api_key or not settings.api_secret:
            logger.error(
                f"Binance API credentials not configured for user {user.username}"
            )
            return "Binance API credentials not configured"

        # Inicializar cliente Binance
        client = Client(settings.api_key, settings.api_secret)

        # Obtener precio actual
        ticker = client.futures_symbol_ticker(symbol=operation.symbol)
        current_price = float(ticker["price"])

        # Cerrar posición
        side = "SELL" if operation.direction == "long" else "BUY"
        order = client.futures_create_order(
            symbol=operation.symbol,
            side=side,
            type="MARKET",
            quantity=float(operation.quantity),
        )

        # Calcular resultados
        entry_price = float(operation.entry_price)
        price_change = ((current_price - entry_price) / entry_price) * 100
        if operation.direction == "short":
            price_change = -price_change

        profit = price_change * operation.leverage
        profit_usd = float(operation.investment) * (profit / 100)

        # Actualizar operación
        operation.status = "closed"
        operation.exit_price = Decimal(str(current_price))
        operation.profit_loss = Decimal(str(profit_usd))
        operation.profit_loss_percentage = Decimal(str(profit))
        operation.closed_at = timezone.now()
        operation.save()

        # Actualizar estado del bot
        bot_status = models.BotStatus.objects.get(user=user)
        if (
            bot_status.current_operation
            and bot_status.current_operation.id == operation.id
        ):
            bot_status.current_operation = None
            bot_status.status = "listening"
            bot_status.save()

        # Enviar notificación de Telegram si está configurado
        if settings.telegram_bot_token and settings.telegram_chat_id:
            send_telegram_notification.delay(
                user_id=user.id,
                message=f"Position closed:\n\n{utils.format_operation_result(operation)}",
            )

        logger.info(
            f"Position closed for user {user.username}: {operation.symbol}"
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
    open_operations = models.Operation.objects.filter(status="open")

    for operation in open_operations:
        try:
            user = operation.user
            settings = models.TradingSettings.objects.get(user=user)

            # Verificar credenciales de Binance
            if not settings.api_key or not settings.api_secret:
                continue

            # Inicializar cliente Binance
            client = Client(settings.api_key, settings.api_secret)

            # Obtener precio actual
            ticker = client.futures_symbol_ticker(symbol=operation.symbol)
            current_price = float(ticker["price"])

            # Calcular ganancia/pérdida actual
            entry_price = float(operation.entry_price)
            price_change = ((current_price - entry_price) / entry_price) * 100
            if operation.direction == "short":
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
def send_telegram_notification(user_id, message):
    """Envía una notificación por Telegram"""
    try:
        import telebot

        user = User.objects.get(id=user_id)
        settings = models.TradingSettings.objects.get(user=user)

        if not settings.telegram_bot_token or not settings.telegram_chat_id:
            return "Telegram not configured"

        bot = telebot.TeleBot(settings.telegram_bot_token)
        bot.send_message(settings.telegram_chat_id, message)

        return "Notification sent"
    except Exception as e:
        logger.error(f"Error sending Telegram notification: {str(e)}")
        return f"Error sending notification: {str(e)}"


@shared_task
def start_bot(user_id):
    """Inicia el bot para un usuario"""
    try:
        user = User.objects.get(id=user_id)
        bot_status, created = models.BotStatus.objects.get_or_create(user=user)

        bot_status.status = "listening"
        bot_status.save()

        logger.info(f"Bot started for user {user.username}")

        # Enviar notificación
        settings = models.TradingSettings.objects.get(user=user)
        if settings.telegram_bot_token and settings.telegram_chat_id:
            send_telegram_notification.delay(
                user_id=user_id, message="Bot started and listening for signals"
            )

        return f"Bot started for user {user_id}"
    except Exception as e:
        logger.error(f"Error starting bot for user {user_id}: {str(e)}")
        return f"Error starting bot: {str(e)}"


@shared_task
def stop_bot(user_id):
    """Detiene el bot para un usuario"""
    try:
        user = User.objects.get(id=user_id)
        bot_status, _ = models.models.BotStatus.objects.get_or_create(user=user)

        bot_status.status = "idle"
        bot_status.save()

        logger.info(f"Bot stopped for user {user.username}")

        # Enviar notificación
        settings = models.TradingSettings.objects.get(user=user)
        if settings.telegram_bot_token and settings.telegram_chat_id:
            message = "Bot stopped"
            if bot_status.current_operation:
                message += ". Warning: There is an open position."

            send_telegram_notification.delay(user_id=user_id, message=message)

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
