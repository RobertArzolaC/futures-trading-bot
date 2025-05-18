import numpy as np
import ta

from apps.trading import choices
from apps.trading.strategies._base import TradingStrategy


class VolatilityBreakoutStrategy(TradingStrategy):
    """
    Estrategia de breakout con análisis de volatilidad para timeframes de 15 minutos.
    Captura movimientos explosivos después de contracciones de volatilidad.
    Ideal para crypto intradía cuando hay noticias o desarrollos importantes.
    """

    def generate_signal(self):
        # Datos
        open_prices = self.df["open"]
        high_prices = self.df["high"]
        low_prices = self.df["low"]
        close_prices = self.df["close"]
        volumes = self.df["volume"]

        # Ventanas de tiempo relevantes para 15 minutos
        squeeze_window = 20  # 5 horas
        breakout_window = 4  # 1 hora

        # --- Análisis de volatilidad ---

        # 1. Bollinger Bands para medir constricción
        bb = ta.volatility.BollingerBands(
            close=close_prices, window=20, window_dev=2
        )

        bb_width = (bb.bollinger_hband() - bb.bollinger_lband()) / close_prices
        bb_avg_width = bb_width.rolling(window=squeeze_window).mean()

        # 2. Keltner Channels para complementar BBs
        typical_price = (high_prices + low_prices + close_prices) / 3

        atr = ta.volatility.AverageTrueRange(
            high=high_prices, low=low_prices, close=close_prices, window=14
        ).average_true_range()

        keltner_middle = typical_price.ewm(span=20).mean()
        keltner_upper = keltner_middle + (1.5 * atr)
        keltner_lower = keltner_middle - (1.5 * atr)

        # Ancho de Keltner Channel
        kc_width = (keltner_upper - keltner_lower) / close_prices

        # 3. Detectar "squeeze" (BB dentro de KC)
        squeeze = (bb.bollinger_hband() < keltner_upper) & (
            bb.bollinger_lband() > keltner_lower
        )

        # 4. Detección de constricción de volatilidad
        # TTM Squeeze personalizado para 15 minutos
        bb_width_percentile = bb_width.rolling(window=squeeze_window).apply(
            lambda x: sum(1 for i in x if i < x.iloc[-1]) / len(x) * 100
        )

        volatility_contraction = bb_width < bb_avg_width * 0.85

        # 5. Momentum durante y después del squeeze
        # Usar linreg slope como indicador de momentum
        momentum_window = 8

        # Función para calcular pendiente de regresión lineal
        def lin_reg_slope(y):
            if len(y) < 2:
                return 0
            x = np.array(range(len(y)))
            y = np.array(y)
            A = np.vstack([x, np.ones(len(x))]).T
            try:
                slope, _ = np.linalg.lstsq(A, y, rcond=None)[0]
                return slope
            except:
                return 0

        # Calcular pendiente sobre precio y volumen
        price_slopes = []
        for i in range(momentum_window, len(close_prices)):
            window_prices = close_prices.iloc[i - momentum_window : i].values
            price_slopes.append(lin_reg_slope(window_prices))

        # Añadir valores iniciales para mantener longitud
        price_slopes = [0] * momentum_window + price_slopes

        # Convertir a pandas Series
        momentum_oscillator = pd.Series(price_slopes, index=close_prices.index)

        # Normalizar para comparabilidad
        normalized_momentum = momentum_oscillator / atr

        # --- Identificación de breakouts ---

        # 1. Breakout de precio
        # Calcular máximo y mínimo de N períodos anteriores
        high_lookback = (
            high_prices.rolling(window=breakout_window).max().shift(1)
        )
        low_lookback = low_prices.rolling(window=breakout_window).min().shift(1)

        # 2. Calcular volumen relativo
        rel_volume = volumes / volumes.rolling(window=20).mean()

        # Datos actuales para comparación
        current_close = close_prices.iloc[-1]
        current_high = high_prices.iloc[-1]
        current_low = low_prices.iloc[-1]
        current_volume = volumes.iloc[-1]

        # --- Generar señales ---

        # Analizar condiciones actuales de volatilidad
        current_squeeze = squeeze.iloc[-1]
        previous_squeeze = squeeze.iloc[-2:-breakout_window].any()
        volatility_expanding = bb_width.iloc[-1] > bb_width.iloc[-2]

        # Analizar momentum
        current_momentum = normalized_momentum.iloc[-1]
        momentum_direction = current_momentum > 0
        momentum_accelerating = abs(current_momentum) > abs(
            normalized_momentum.iloc[-2]
        )

        # Confirmar breakout de precio
        upside_breakout = (current_high > high_lookback.iloc[-1]) and (
            current_close > high_lookback.iloc[-1] * 1.001
        )
        downside_breakout = (current_low < low_lookback.iloc[-1]) and (
            current_close < low_lookback.iloc[-1] * 0.999
        )

        # Confirmar con volumen
        volume_confirmation = rel_volume.iloc[-1] > 1.3

        # --- Escenarios de trading ---

        # 1. Breakout después de squeeze
        squeeze_breakout_bull = (
            previous_squeeze
            and not current_squeeze
            and upside_breakout
            and momentum_direction
            and volume_confirmation
        )

        squeeze_breakout_bear = (
            previous_squeeze
            and not current_squeeze
            and downside_breakout
            and not momentum_direction
            and volume_confirmation
        )

        # 2. Breakout con expansión de volatilidad
        vol_expansion_bull = (
            volatility_contraction.iloc[-4:-2].any()
            and volatility_expanding
            and upside_breakout
            and current_momentum > 0
            and momentum_accelerating
        )

        vol_expansion_bear = (
            volatility_contraction.iloc[-4:-2].any()
            and volatility_expanding
            and downside_breakout
            and current_momentum < 0
            and momentum_accelerating
        )

        # 3. Breakout fuerte tras acumulación
        high_volume_breakout_bull = (
            upside_breakout
            and rel_volume.iloc[-1] > 2.0  # Volumen muy superior al promedio
            and current_momentum > 0
            and (current_close - current_low)
            > 0.3
            * (
                current_high - current_low
            )  # Cierre en la parte superior del rango
        )

        high_volume_breakout_bear = (
            downside_breakout
            and rel_volume.iloc[-1] > 2.0  # Volumen muy superior al promedio
            and current_momentum < 0
            and (current_high - current_close)
            > 0.3
            * (
                current_high - current_low
            )  # Cierre en la parte inferior del rango
        )

        # Análisis adicional de precio para evitar falsas señales
        strong_candle_bull = (current_close > open_prices.iloc[-1]) and (
            current_close - open_prices.iloc[-1]
        ) / (current_high - current_low) > 0.7
        strong_candle_bear = (current_close < open_prices.iloc[-1]) and (
            open_prices.iloc[-1] - current_close
        ) / (current_high - current_low) > 0.7

        # Combinar todas las condiciones
        buy_conditions = [
            (squeeze_breakout_bull and strong_candle_bull),
            (vol_expansion_bull and volume_confirmation),
            high_volume_breakout_bull,
        ]

        sell_conditions = [
            (squeeze_breakout_bear and strong_candle_bear),
            (vol_expansion_bear and volume_confirmation),
            high_volume_breakout_bear,
        ]

        # Generar señal final
        if any(buy_conditions):
            return self._build_signal(choices.OrderSide.BUY)
        elif any(sell_conditions):
            return self._build_signal(choices.OrderSide.SELL)

        return self._build_signal(choices.OrderSide.HOLD)
