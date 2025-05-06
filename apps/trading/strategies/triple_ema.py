from apps.trading import choices
from apps.trading.strategies._base import TradingStrategy


class TripleEMAStrategy(TradingStrategy):
    def generate_signal(self) -> str:
        ema10 = self.df["close"].ewm(span=10).mean()
        ema20 = self.df["close"].ewm(span=20).mean()
        ema50 = self.df["close"].ewm(span=50).mean()

        if (
            ema10.iloc[-2] < ema20.iloc[-2] < ema50.iloc[-2]
            and ema10.iloc[-1] > ema20.iloc[-1] > ema50.iloc[-1]
        ):
            return self._build_signal(choices.OrderSide.BUY)
        elif (
            ema10.iloc[-2] > ema20.iloc[-2] > ema50.iloc[-2]
            and ema10.iloc[-1] < ema20.iloc[-1] < ema50.iloc[-1]
        ):
            return self._build_signal(choices.OrderSide.SELL)
        return self._build_signal(choices.OrderSide.HOLD)
