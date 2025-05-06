import ta

from apps.trading import choices
from apps.trading.strategies._base import TradingStrategy


class MACDDivergenceStrategy(TradingStrategy):
    def generate_signal(self):
        # Calcular MACD
        macd = ta.trend.MACD(self.df["close"])
        self.df["macd"] = macd.macd()
        self.df["macd_signal"] = macd.macd_signal()
        self.df["macd_diff"] = macd.macd_diff()

        # Buscar divergencias (últimas 14 velas)
        look_back = 14

        # Divergencia alcista: precio hace mínimos más bajos pero MACD hace mínimos más altos
        price_lower_low = (
            self.df["close"].iloc[-1] < self.df["close"].iloc[-look_back:].min()
        )
        macd_higher_low = (
            self.df["macd"].iloc[-1] > self.df["macd"].iloc[-look_back:].min()
        )

        # Divergencia bajista: precio hace máximos más altos pero MACD hace máximos más bajos
        price_higher_high = (
            self.df["close"].iloc[-1] > self.df["close"].iloc[-look_back:].max()
        )
        macd_lower_high = (
            self.df["macd"].iloc[-1] < self.df["macd"].iloc[-look_back:].max()
        )

        # Señales basadas en divergencias
        if price_lower_low and macd_higher_low:
            return self._build_signal(choices.OrderSide.BUY)
        elif price_higher_high and macd_lower_high:
            return self._build_signal(choices.OrderSide.SELL)

        return self._build_signal(choices.OrderSide.HOLD)
