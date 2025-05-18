import numpy as np
import ta

from apps.trading import choices
from apps.trading.strategies._base import TradingStrategy


class ShortTermTrendCatcherStrategy(TradingStrategy):
    """
    Estrategia cazadora de tendencias de corto plazo optimizada para 15 minutos.
    Utiliza una combinación de impulso, volatilidad y análisis técnico para
    capturar movimientos tendenciales antes de que se desarrollen completamente.
    Ideal para crypto con tendencias intradiarias.
    """

    def generate_signal(self):
        # Parámetros optimizados para 15 minutos
        lookback_short = 8  # 2 horas
        lookback_medium = 24  # 6 horas

        # Series de datos
        open_prices = self.df["open"]
        high_prices = self.df["high"]
        low_prices = self.df["low"]
        close_prices = self.df["close"]
        volumes = self.df["volume"]

        # --- Indicadores para detección de tendencias ---

        # 1. EMAs múltiples para confirmar tendencia
        ema5 = close_prices.ewm(span=5).mean()
        ema8 = close_prices.ewm(span=8).mean()
        ema13 = close_prices.ewm(span=13).mean()
        ema21 = close_prices.ewm(span=21).mean()
        ema34 = close_prices.ewm(span=34).mean()

        # 2. Hull Moving Average para identificar cambios de tendencia antes
        # Versión simplificada de HMA
        wma1 = close_prices.rolling(
            window=9
        ).mean()  # Simple WMA para simplificar
        wma2 = close_prices.rolling(window=4).mean()  # WMA más corto

        # Calcular Raw HMA: (2*WMA(n/2) - WMA(n))
        raw_hma = 2 * wma2 - wma1

        # Smoothing final
        hma = raw_hma.rolling(window=4).mean()

        # 3. TSI (True Strength Index) para momentum con menos lag
        # Primera suavización exponencial
        momentum = close_prices.diff()
        abs_momentum = momentum.abs()

        # Suavizar con EMA
        ema_momentum = momentum.ewm(span=13).mean()
        ema_abs_momentum = abs_momentum.ewm(span=13).mean()

        # Segunda suavización
        double_ema_momentum = ema_momentum.ewm(span=7).mean()
        double_ema_abs_momentum = ema_abs_momentum.ewm(span=7).mean()

        # Calcular TSI final (puede variar entre -100 y 100)
        tsi = 100 * (double_ema_momentum / double_ema_abs_momentum)

        # 4. Filtro de ATR para volatilidad
        atr = ta.volatility.AverageTrueRange(
            high=high_prices, low=low_prices, close=close_prices, window=14
        ).average_true_range()

        # Ratio de ATR actual vs promedio para detectar expansión de volatilidad
        atr_ratio = atr / atr.rolling(window=30).mean()

        # 5. Supertrend modificado para timeframe de 15 min
        # Parámetros ajustados para menor timeframe
        factor = 2.0
        atr_period = 10

        # Calcular ATR para Supertrend
        st_atr = ta.volatility.AverageTrueRange(
            high=high_prices,
            low=low_prices,
            close=close_prices,
            window=atr_period,
        ).average_true_range()

        # Calcular bandas
        basic_upperband = ((high_prices + low_prices) / 2) + (factor * st_atr)
        basic_lowerband = ((high_prices + low_prices) / 2) - (factor * st_atr)

        # Inicializar arrays para Supertrend
        final_upperband = np.zeros(len(close_prices))
        final_lowerband = np.zeros(len(close_prices))
        supertrend = np.zeros(len(close_prices))
        trend = np.zeros(len(close_prices))

        # Calcular Supertrend
        for i in range(1, len(close_prices)):
            # Upperband
            if (
                basic_upperband.iloc[i] < final_upperband[i - 1]
                or close_prices.iloc[i - 1] > final_upperband[i - 1]
            ):
                final_upperband[i] = basic_upperband.iloc[i]
            else:
                final_upperband[i] = final_upperband[i - 1]

            # Lowerband
            if (
                basic_lowerband.iloc[i] > final_lowerband[i - 1]
                or close_prices.iloc[i - 1] < final_lowerband[i - 1]
            ):
                final_lowerband[i] = basic_lowerband.iloc[i]
            else:
                final_lowerband[i] = final_lowerband[i - 1]

            # Supertrend
            if (
                supertrend[i - 1] == final_upperband[i - 1]
                and close_prices.iloc[i] <= final_upperband[i]
            ):
                supertrend[i] = final_upperband[i]
            elif (
                supertrend[i - 1] == final_upperband[i - 1]
                and close_prices.iloc[i] > final_upperband[i]
            ):
                supertrend[i] = final_lowerband[i]
            elif (
                supertrend[i - 1] == final_lowerband[i - 1]
                and close_prices.iloc[i] >= final_lowerband[i]
            ):
                supertrend[i] = final_lowerband[i]
            elif (
                supertrend[i - 1] == final_lowerband[i - 1]
                and close_prices.iloc[i] < final_lowerband[i]
            ):
                supertrend[i] = final_upperband[i]

            # Tendencia (1 para bullish, -1 para bearish)
            if supertrend[i] <= close_prices.iloc[i]:
                trend[i] = 1
            else:
                trend[i] = -1

        # --- Análisis del contexto de mercado ---

        # Datos actuales
        current_price = close_prices.iloc[-1]
        current_tsi = tsi.iloc[-1]
        current_atr_ratio = atr_ratio.iloc[-1]

        # Alineación de EMAs (bullish/bearish)
        bullish_alignment = (
            ema5.iloc[-1] > ema8.iloc[-1] > ema13.iloc[-1] > ema21.iloc[-1]
        )
        bearish_alignment = (
            ema5.iloc[-1] < ema8.iloc[-1] < ema13.iloc[-1] < ema21.iloc[-1]
        )

        # Análisis de cruce de EMAs
        ema_cross_up = (
            ema5.iloc[-2] <= ema8.iloc[-2] and ema5.iloc[-1] > ema8.iloc[-1]
        )
        ema_cross_down = (
            ema5.iloc[-2] >= ema8.iloc[-2] and ema5.iloc[-1] < ema8.iloc[-1]
        )

        # Pendiente de HMA
        hma_slope = (hma.iloc[-1] - hma.iloc[-3]) / hma.iloc[-3]

        # Tendencia de Supertrend
        supertrend_bullish = trend[-1] == 1
        supertrend_bearish = trend[-1] == -1

        # Cambio de tendencia en Supertrend
        supertrend_changed_up = trend[-1] == 1 and trend[-2] == -1
        supertrend_changed_down = trend[-1] == -1 and trend[-2] == 1

        # --- Generación de señales de tendencia ---

        # Condiciones alcistas
        bullish_conditions = [
            # Alineación EMA con TSI positivo
            (bullish_alignment and current_tsi > 5),
            # Cruce de EMA con confirmación de Hull MA
            (ema_cross_up and hma_slope > 0.001 and current_tsi > 0),
            # Cambio de Supertrend alcista con volatilidad expandiendo
            (supertrend_changed_up and current_atr_ratio > 1.1),
            # Impulso alcista fuerte con confirmación de Supertrend
            (
                current_tsi > 15
                and current_tsi > tsi.iloc[-2]
                and supertrend_bullish
            ),
            # Momentum creciente en contexto alcista
            (
                current_tsi > 0
                and current_tsi > tsi.iloc[-3] * 1.2
                and hma_slope > 0
            ),
        ]

        # Condiciones bajistas
        bearish_conditions = [
            # Alineación EMA con TSI negativo
            (bearish_alignment and current_tsi < -5),
            # Cruce de EMA con confirmación de Hull MA
            (ema_cross_down and hma_slope < -0.001 and current_tsi < 0),
            # Cambio de Supertrend bajista con volatilidad expandiendo
            (supertrend_changed_down and current_atr_ratio > 1.1),
            # Impulso bajista fuerte con confirmación de Supertrend
            (
                current_tsi < -15
                and current_tsi < tsi.iloc[-2]
                and supertrend_bearish
            ),
            # Momentum decreciente en contexto bajista
            (
                current_tsi < 0
                and current_tsi < tsi.iloc[-3] * 1.2
                and hma_slope < 0
            ),
        ]

        # --- Confirmación con volumen ---
        volume_confirm = volumes.iloc[-1] > volumes.iloc[-5:].mean()
        volume_surge = volumes.iloc[-1] > volumes.iloc[-10:].mean() * 1.5

        # Si hay un surge de volumen, requiere menos confirmaciones
        min_confirmations = 1 if volume_surge else 2

        # Contar cuántas condiciones alcistas/bajistas se cumplen
        bullish_count = sum(1 for cond in bullish_conditions if cond)
        bearish_count = sum(1 for cond in bearish_conditions if cond)

        # Generar señales finales
        if bullish_count >= min_confirmations and (
            volume_confirm or volume_surge
        ):
            return self._build_signal(choices.OrderSide.BUY)
        elif bearish_count >= min_confirmations and (
            volume_confirm or volume_surge
        ):
            return self._build_signal(choices.OrderSide.SELL)

        return self._build_signal(choices.OrderSide.HOLD)
