import ta

from apps.trading import choices
from apps.trading.strategies._base import TradingStrategy


class WyckoffAccumulationStrategy(TradingStrategy):
    """
    Estrategia basada en los principios de Wyckoff adaptada para crypto.
    Identifica fases de acumulación y distribución usando volumen y precio.
    Extremadamente efectiva para detectar tendencias antes de grandes movimientos.
    """

    def generate_signal(self):
        # Calcular indicadores para identificar fases de Wyckoff
        window = 30

        # Volume-Price Trend (VPT)
        vpt = ta.volume.VolumePriceTrendIndicator(
            self.df["close"], self.df["volume"]
        ).volume_price_trend()

        # Average Volume
        avg_volume = self.df["volume"].rolling(window=20).mean()

        # SMA y VWAP para identificar soporte/resistencia
        sma50 = self.df["close"].rolling(window=50).mean()
        typical_price = (
            self.df["high"] + self.df["low"] + self.df["close"]
        ) / 3
        cumulative_tpv = (typical_price * self.df["volume"]).cumsum()
        cumulative_volume = self.df["volume"].cumsum()
        vwap = cumulative_tpv / cumulative_volume

        # Detección de rango
        high_range = self.df["high"].rolling(window=window).max()
        low_range = self.df["low"].rolling(window=window).min()
        range_size = (high_range - low_range) / low_range

        # Detectar compresión de precio (característica de acumulación)
        price_compression = range_size.iloc[-1] < 0.05  # Menos de 5% de rango

        # Detectar springs y upthrusts (conceptos de Wyckoff)
        current_price = self.df["close"].iloc[-1]
        recent_low = self.df["low"].iloc[-5:].min()
        recent_high = self.df["high"].iloc[-5:].max()

        # Spring: Precio rompe soporte pero cierra por encima
        spring = (
            self.df["low"].iloc[-1] < low_range.iloc[-5]
            and current_price > low_range.iloc[-1]
        )

        # Upthrust: Precio rompe resistencia pero cierra por debajo
        upthrust = (
            self.df["high"].iloc[-1] > high_range.iloc[-5]
            and current_price < high_range.iloc[-1]
        )

        # Análisis de volumen durante movimientos
        volume_surge = self.df["volume"].iloc[-1] > avg_volume.iloc[-1] * 1.5

        # Identificar fase de acumulación
        if price_compression:
            # Fase de spring con volumen - señal de compra fuerte
            if spring and volume_surge:
                return self._build_signal(choices.OrderSide.BUY)

            # Breakout de rango de acumulación
            if current_price > high_range.iloc[-2] and volume_surge:
                return self._build_signal(choices.OrderSide.BUY)

        # Identificar fase de distribución
        if price_compression:
            # Upthrust con volumen - señal de venta fuerte
            if upthrust and volume_surge:
                return self._build_signal(choices.OrderSide.SELL)

            # Breakdown de rango de distribución
            if current_price < low_range.iloc[-2] and volume_surge:
                return self._build_signal(choices.OrderSide.SELL)

        # Análisis adicional de fuerza/debilidad
        vpt_trend = vpt.iloc[-1] > vpt.iloc[-10]
        price_trend = current_price > self.df["close"].iloc[-10]

        # Divergencia de fuerza: VPT sube, precio lateral o baja (acumulación)
        if vpt_trend and not price_trend and price_compression:
            return self._build_signal(choices.OrderSide.BUY)

        # Divergencia de debilidad: VPT baja, precio lateral o sube (distribución)
        if not vpt_trend and price_trend and price_compression:
            return self._build_signal(choices.OrderSide.SELL)

        return self._build_signal(choices.OrderSide.HOLD)
