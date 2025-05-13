import ta

from apps.trading import choices
from apps.trading.strategies._base import TradingStrategy


class OBVDivergenceStrategy(TradingStrategy):
    """
    Estrategia basada en On-Balance Volume (OBV) con divergencias.
    Extremadamente efectiva en crypto para detectar acumulación/distribución
    antes de movimientos importantes de precio.
    """

    def generate_signal(self):
        # Calcular OBV
        obv_indicator = ta.volume.OnBalanceVolumeIndicator(
            self.df["close"], self.df["volume"]
        )
        obv = obv_indicator.on_balance_volume()

        # Suavizar OBV con EMA
        obv_ema = obv.ewm(span=10).mean()

        # Calcular EMA del precio para tendencia
        price_ema = self.df["close"].ewm(span=20).mean()

        # Buscar divergencias en ventana de 20 períodos
        window = 20

        if len(self.df) < window:
            return self._build_signal(choices.OrderSide.HOLD)

        # Encontrar máximos y mínimos locales
        price_window = self.df["close"].iloc[-window:]
        obv_window = obv_ema.iloc[-window:]

        # Índices de máximos y mínimos
        price_high_idx = price_window.idxmax()
        price_low_idx = price_window.idxmin()
        obv_high_idx = obv_window.idxmax()
        obv_low_idx = obv_window.idxmin()

        current_price = self.df["close"].iloc[-1]
        current_obv = obv_ema.iloc[-1]

        # Divergencia alcista: precio hace mínimo más bajo, OBV hace mínimo más alto
        if (
            price_low_idx > len(self.df) - 10  # Mínimo reciente
            and obv_low_idx > len(self.df) - 10
        ):
            prev_price_low = (
                self.df["close"]
                .iloc[price_low_idx - window : price_low_idx]
                .min()
            )
            prev_obv_low = obv_ema.iloc[
                obv_low_idx - window : obv_low_idx
            ].min()

            if (
                self.df["close"].iloc[price_low_idx] < prev_price_low
                and obv_ema.iloc[obv_low_idx] > prev_obv_low
            ):
                # Confirmar con cambio de tendencia
                if current_price > self.df["close"].iloc[-3]:
                    return self._build_signal(choices.OrderSide.BUY)

        # Divergencia bajista: precio hace máximo más alto, OBV hace máximo más bajo
        if (
            price_high_idx > len(self.df) - 10  # Máximo reciente
            and obv_high_idx > len(self.df) - 10
        ):
            prev_price_high = (
                self.df["close"]
                .iloc[price_high_idx - window : price_high_idx]
                .max()
            )
            prev_obv_high = obv_ema.iloc[
                obv_high_idx - window : obv_high_idx
            ].max()

            if (
                self.df["close"].iloc[price_high_idx] > prev_price_high
                and obv_ema.iloc[obv_high_idx] < prev_obv_high
            ):
                # Confirmar con cambio de tendencia
                if current_price < self.df["close"].iloc[-3]:
                    return self._build_signal(choices.OrderSide.SELL)

        # Señales adicionales por cambios bruscos en OBV
        obv_change = (current_obv - obv_ema.iloc[-5]) / obv_ema.iloc[-5]
        price_change = (current_price - self.df["close"].iloc[-5]) / self.df[
            "close"
        ].iloc[-5]

        # OBV sube fuertemente pero precio no: señal de compra
        if obv_change > 0.05 and price_change < 0.01:
            return self._build_signal(choices.OrderSide.BUY)

        # OBV cae fuertemente pero precio no: señal de venta
        elif obv_change < -0.05 and price_change > -0.01:
            return self._build_signal(choices.OrderSide.SELL)

        return self._build_signal(choices.OrderSide.HOLD)
