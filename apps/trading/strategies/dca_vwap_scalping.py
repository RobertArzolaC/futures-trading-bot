import ta

from apps.trading import choices
from apps.trading.strategies._base import TradingStrategy


class DCAVWAPScalpingStrategy(TradingStrategy):
    """
    Estrategia de scalping basada en VWAP con DCA (Dollar Cost Averaging).
    Ideal para trading intradía en crypto con alta frecuencia.
    Usa VWAP como punto de referencia y RSI para timing.
    """

    def generate_signal(self):
        # Calcular VWAP (Volume Weighted Average Price)
        typical_price = (
            self.df["high"] + self.df["low"] + self.df["close"]
        ) / 3
        cumulative_tpv = (typical_price * self.df["volume"]).cumsum()
        cumulative_volume = self.df["volume"].cumsum()
        vwap = cumulative_tpv / cumulative_volume

        # RSI para confirmar momentum
        rsi = ta.momentum.RSIIndicator(self.df["close"], window=7).rsi()

        # Calcular desviación del precio respecto a VWAP
        current_price = self.df["close"].iloc[-1]
        current_vwap = vwap.iloc[-1]
        price_deviation = (current_price - current_vwap) / current_vwap

        # Calcular pendiente de VWAP para determinar tendencia
        if len(vwap) >= 5:
            vwap_slope = (vwap.iloc[-1] - vwap.iloc[-5]) / vwap.iloc[-5]
        else:
            vwap_slope = 0

        # Calcular volumen relativo
        avg_volume = self.df["volume"].rolling(window=20).mean()
        relative_volume = self.df["volume"].iloc[-1] / avg_volume.iloc[-1]

        # Estrategia de scalping con múltiples condiciones
        # Compra: precio por debajo de VWAP, RSI oversold, alto volumen
        if (
            price_deviation < -0.005  # Precio 0.5% debajo de VWAP
            and rsi.iloc[-1] < 35  # RSI oversold
            and relative_volume > 1.2  # Volumen 20% por encima del promedio
            and vwap_slope > -0.001
        ):  # VWAP no en fuerte bajada
            return self._build_signal(choices.OrderSide.BUY)

        # Venta: precio por encima de VWAP, RSI overbought, alto volumen
        elif (
            price_deviation > 0.005  # Precio 0.5% encima de VWAP
            and rsi.iloc[-1] > 65  # RSI overbought
            and relative_volume > 1.2  # Volumen 20% por encima del promedio
            and vwap_slope < 0.001
        ):  # VWAP no en fuerte subida
            return self._build_signal(choices.OrderSide.SELL)

        return self._build_signal(choices.OrderSide.HOLD)
