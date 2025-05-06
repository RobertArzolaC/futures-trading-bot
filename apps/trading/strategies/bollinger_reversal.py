import ta

from apps.trading import choices
from apps.trading.strategies._base import TradingStrategy


class BollingerReversalStrategy(TradingStrategy):
    def generate_signal(self):
        bb = ta.volatility.BollingerBands(
            self.df["close"], window=20, window_dev=2
        )
        self.df["bb_upper"] = bb.bollinger_hband()
        self.df["bb_lower"] = bb.bollinger_lband()
        last_price = self.df["close"].iloc[-1]

        if last_price < self.df["bb_lower"].iloc[-1]:
            return self._build_signal(choices.OrderSide.BUY)
        elif last_price > self.df["bb_upper"].iloc[-1]:
            return self._build_signal(choices.OrderSide.SELL)
        return self._build_signal(choices.OrderSide.HOLD)
