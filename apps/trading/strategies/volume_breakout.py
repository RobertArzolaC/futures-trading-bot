import ta

from apps.trading import choices
from apps.trading.strategies._base import TradingStrategy


class VolumeBreakoutStrategy(TradingStrategy):
    """
    Estrategia de breakout por volumen optimizada para timeframes de 15 minutos.
    Detecta rupturas de niveles clave con confirmación por volumen y análisis de volatilidad.
    Ideal para capturar el inicio de nuevas tendencias en mercados cripto intradía.
    """

    def generate_signal(self):
        # Parámetros optimizados para 15 minutos
        lookback = 24  # 6 horas de datos (24 velas de 15 min)

        # Calcular niveles clave
        recent_high = self.df["high"].rolling(window=lookback).max()
        recent_low = self.df["low"].rolling(window=lookback).min()

        # Calcular ATR para la volatilidad (más ajustado para 15 min)
        atr = ta.volatility.AverageTrueRange(
            self.df["high"], self.df["low"], self.df["close"], window=14
        ).average_true_range()

        # Análisis de volumen
        volume_ma = self.df["volume"].rolling(window=20).mean()
        rel_volume = self.df["volume"] / volume_ma
        high_volume = rel_volume > 1.5  # 50% más volumen del promedio

        # Análisis de momentum para confirmar dirección
        rsi = ta.momentum.RSIIndicator(self.df["close"], window=9).rsi()

        # Soporte/Resistencia dinámicos basados en Fibonacci y precio reciente
        price_range = recent_high - recent_low
        fib_38_level = recent_low + 0.382 * price_range
        fib_62_level = recent_low + 0.618 * price_range

        # Datos actuales
        current_price = self.df["close"].iloc[-1]
        prev_close = self.df["close"].iloc[-2]
        current_atr = atr.iloc[-1]
        current_rsi = rsi.iloc[-1]

        # Detección de breakout alcista
        # El precio rompe resistencia con alto volumen y buena distancia
        breakout_up = (
            current_price
            > recent_high.iloc[-2] * 1.001  # 0.1% encima para confirmar
            and self.df["volume"].iloc[-1]
            > volume_ma.iloc[-1] * 1.4  # Confirmación volumen
            and current_price > prev_close  # Cierre alcista
            and self.df["close"].iloc[-1] - self.df["open"].iloc[-1]
            > 0.3 * current_atr  # Rango significativo
        )

        # Detección de breakout bajista
        # El precio rompe soporte con alto volumen y buena distancia
        breakout_down = (
            current_price
            < recent_low.iloc[-2] * 0.999  # 0.1% debajo para confirmar
            and self.df["volume"].iloc[-1]
            > volume_ma.iloc[-1] * 1.4  # Confirmación volumen
            and current_price < prev_close  # Cierre bajista
            and self.df["open"].iloc[-1] - self.df["close"].iloc[-1]
            > 0.3 * current_atr  # Rango significativo
        )

        # Detección de falsos breakouts para tomar posición contraria
        # Estos son muy rentables en timeframes de 15 minutos
        false_breakout_up = (
            self.df["high"].iloc[-1] > recent_high.iloc[-2]
            and current_price < recent_high.iloc[-2]
            and current_price < self.df["open"].iloc[-1]
            and current_rsi > 70  # Sobrecomprado
        )

        false_breakout_down = (
            self.df["low"].iloc[-1] < recent_low.iloc[-2]
            and current_price > recent_low.iloc[-2]
            and current_price > self.df["open"].iloc[-1]
            and current_rsi < 30  # Sobrevendido
        )

        # Detección de pull-backs a zonas Fibonacci después de breakouts
        # Muy comunes en 15 minutos después de un breakout inicial
        pullback_to_support = (
            self.df["close"].iloc[-3]
            > self.df["close"].iloc[-2]  # Retroceso reciente
            and fib_62_level
            < current_price
            < fib_38_level  # En zona de retroceso Fibonacci
            and current_price > prev_close  # Rebota
            and current_rsi < 45  # No sobrecomprado
        )

        pullback_to_resistance = (
            self.df["close"].iloc[-3]
            < self.df["close"].iloc[-2]  # Retroceso reciente
            and fib_38_level
            < current_price
            < fib_62_level  # En zona de retroceso Fibonacci
            and current_price < prev_close  # Rebota
            and current_rsi > 55  # No sobrevendido
        )

        # Generar señales
        if breakout_up or false_breakout_down or pullback_to_support:
            return self._build_signal(choices.OrderSide.BUY)
        elif breakout_down or false_breakout_up or pullback_to_resistance:
            return self._build_signal(choices.OrderSide.SELL)

        return self._build_signal(choices.OrderSide.HOLD)
