import numpy as np
import ta

from apps.trading import choices
from apps.trading.strategies._base import TradingStrategy


class PriceActionPatternStrategy(TradingStrategy):
    """
    Estrategia basada en patrones de Price Action optimizada para 15 minutos.
    Detecta formaciones de velas y patrones de precio de alta precisión.
    Ideal para traders discrecionales que buscan automatizar patrones conocidos.
    """

    def generate_signal(self):
        # Asegurar que tenemos suficientes datos
        if len(self.df) < 20:
            return self._build_signal(choices.OrderSide.HOLD)

        # Series de precios para facilitar el cálculo
        open_prices = self.df["open"]
        high_prices = self.df["high"]
        low_prices = self.df["low"]
        close_prices = self.df["close"]
        volumes = self.df["volume"]

        # Calcular parámetros
        body_sizes = abs(close_prices - open_prices)
        avg_body_size = body_sizes.rolling(window=14).mean()
        upper_wicks = high_prices - np.maximum(close_prices, open_prices)
        lower_wicks = np.minimum(close_prices, open_prices) - low_prices

        # ATR para normalizar los patrones
        atr = ta.volatility.AverageTrueRange(
            high_prices, low_prices, close_prices, window=14
        ).average_true_range()

        # Tendencia reciente (útil para contextualizar patrones)
        ema8 = close_prices.ewm(span=8).mean()
        ema21 = close_prices.ewm(span=21).mean()
        uptrend = ema8 > ema21

        # Función para identificar velas alcistas/bajistas
        def is_bullish(i):
            return close_prices.iloc[i] > open_prices.iloc[i]

        def is_bearish(i):
            return close_prices.iloc[i] < open_prices.iloc[i]

        # --- Detección de patrones de Price Action ---

        # 1. Patrón de Engulfing (muy efectivo en 15 min)
        bullish_engulfing = (
            is_bearish(-2)
            and is_bullish(-1)
            and open_prices.iloc[-1] <= close_prices.iloc[-2]
            and close_prices.iloc[-1] >= open_prices.iloc[-2]
            and body_sizes.iloc[-1] > avg_body_size.iloc[-1] * 1.2
        )

        bearish_engulfing = (
            is_bullish(-2)
            and is_bearish(-1)
            and open_prices.iloc[-1] >= close_prices.iloc[-2]
            and close_prices.iloc[-1] <= open_prices.iloc[-2]
            and body_sizes.iloc[-1] > avg_body_size.iloc[-1] * 1.2
        )

        # 2. Patrón Pin Bar / Hammer
        bullish_pin = (
            lower_wicks.iloc[-1] > 2 * body_sizes.iloc[-1]
            and upper_wicks.iloc[-1] < body_sizes.iloc[-1]
            and lower_wicks.iloc[-1] > atr.iloc[-1] * 0.5
            and not uptrend.iloc[-2]  # Más efectivo en downtrend
        )

        bearish_pin = (
            upper_wicks.iloc[-1] > 2 * body_sizes.iloc[-1]
            and lower_wicks.iloc[-1] < body_sizes.iloc[-1]
            and upper_wicks.iloc[-1] > atr.iloc[-1] * 0.5
            and uptrend.iloc[-2]  # Más efectivo en uptrend
        )

        # 3. Patrón Inside Bar (consolidación seguida de breakout)
        inside_bar = (
            high_prices.iloc[-2] > high_prices.iloc[-1]
            and low_prices.iloc[-2] < low_prices.iloc[-1]
        )

        # 4. Patrón Outside Bar (volatilidad y posible reversión)
        outside_bar = (
            high_prices.iloc[-1] > high_prices.iloc[-2]
            and low_prices.iloc[-1] < low_prices.iloc[-2]
        )

        # 5. Vela Estrella Matutina/Vespertina (patrón de 3 velas)
        morning_star = (
            is_bearish(-3)
            and body_sizes.iloc[-3] > avg_body_size.iloc[-3]
            and body_sizes.iloc[-2] < avg_body_size.iloc[-2] * 0.6
            and is_bullish(-1)
            and close_prices.iloc[-1]
            > (open_prices.iloc[-3] + close_prices.iloc[-3]) / 2
        )

        evening_star = (
            is_bullish(-3)
            and body_sizes.iloc[-3] > avg_body_size.iloc[-3]
            and body_sizes.iloc[-2] < avg_body_size.iloc[-2] * 0.6
            and is_bearish(-1)
            and close_prices.iloc[-1]
            < (open_prices.iloc[-3] + close_prices.iloc[-3]) / 2
        )

        # 6. Patrón de Rechazo de Nivel (15 min muy efectivo)
        key_level_rejection_bull = (
            low_prices.iloc[-1] < low_prices.iloc[-10:].min() * 1.005
            and close_prices.iloc[-1]
            > (open_prices.iloc[-1] + close_prices.iloc[-1]) / 2
            and volumes.iloc[-1] > volumes.iloc[-5:].mean() * 1.3
        )

        key_level_rejection_bear = (
            high_prices.iloc[-1] > high_prices.iloc[-10:].max() * 0.995
            and close_prices.iloc[-1]
            < (open_prices.iloc[-1] + close_prices.iloc[-1]) / 2
            and volumes.iloc[-1] > volumes.iloc[-5:].mean() * 1.3
        )

        # 7. Pullback a EMA (muy común en 15 min)
        pullback_to_ema_bull = (
            uptrend.iloc[-1]
            and min(
                low_prices.iloc[-3], low_prices.iloc[-2], low_prices.iloc[-1]
            )
            <= ema21.iloc[-1]
            <= close_prices.iloc[-1]
            and close_prices.iloc[-1] > open_prices.iloc[-1]
        )

        pullback_to_ema_bear = (
            not uptrend.iloc[-1]
            and max(
                high_prices.iloc[-3], high_prices.iloc[-2], high_prices.iloc[-1]
            )
            >= ema21.iloc[-1]
            >= close_prices.iloc[-1]
            and close_prices.iloc[-1] < open_prices.iloc[-1]
        )

        # 8. Doble/Triple techo o suelo (patrones multi-vela)
        # Simplificado para 15 min (versión más precisa requeriría algoritmo de picos)
        last_10_highs = high_prices.iloc[-10:].tolist()
        last_10_lows = low_prices.iloc[-10:].tolist()

        recent_tops = [
            i
            for i in range(1, len(last_10_highs) - 1)
            if last_10_highs[i] > last_10_highs[i - 1]
            and last_10_highs[i] > last_10_highs[i + 1]
        ]

        recent_bottoms = [
            i
            for i in range(1, len(last_10_lows) - 1)
            if last_10_lows[i] < last_10_lows[i - 1]
            and last_10_lows[i] < last_10_lows[i + 1]
        ]

        # Cálculo simplificado para doble techo/suelo
        double_top = (
            len(recent_tops) >= 2
            and abs(
                last_10_highs[recent_tops[-1]] - last_10_highs[recent_tops[-2]]
            )
            / atr.iloc[-1]
            < 0.2
            and close_prices.iloc[-1] < open_prices.iloc[-1]
        )

        double_bottom = (
            len(recent_bottoms) >= 2
            and abs(
                last_10_lows[recent_bottoms[-1]]
                - last_10_lows[recent_bottoms[-2]]
            )
            / atr.iloc[-1]
            < 0.2
            and close_prices.iloc[-1] > open_prices.iloc[-1]
        )

        # --- Generación de señales basadas en patrones ---

        # Patrones alcistas
        bullish_patterns = (
            bullish_engulfing
            or bullish_pin
            or morning_star
            or key_level_rejection_bull
            or pullback_to_ema_bull
            or double_bottom
            or (inside_bar and uptrend.iloc[-1])
        )

        # Patrones bajistas
        bearish_patterns = (
            bearish_engulfing
            or bearish_pin
            or evening_star
            or key_level_rejection_bear
            or pullback_to_ema_bear
            or double_top
            or (inside_bar and not uptrend.iloc[-1])
        )

        # --- Confirmar con volumen y precio ---
        vol_confirm = volumes.iloc[-1] > volumes.iloc[-5:].mean()
        price_confirm_bull = close_prices.iloc[-1] > open_prices.iloc[-1]
        price_confirm_bear = close_prices.iloc[-1] < open_prices.iloc[-1]

        # Generar señales finales
        if bullish_patterns and (vol_confirm or price_confirm_bull):
            return self._build_signal(choices.OrderSide.BUY)
        elif bearish_patterns and (vol_confirm or price_confirm_bear):
            return self._build_signal(choices.OrderSide.SELL)

        return self._build_signal(choices.OrderSide.HOLD)
