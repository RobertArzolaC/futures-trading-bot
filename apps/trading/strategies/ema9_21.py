from apps.trading import choices
from apps.trading.strategies._base import TradingStrategy


class EMA9_21Strategy(TradingStrategy):
    def generate_signal(self) -> str:
        ema9 = self.df["close"].ewm(span=9).mean()
        ema21 = self.df["close"].ewm(span=21).mean()

        if ema9.iloc[-2] < ema21.iloc[-2] and ema9.iloc[-1] > ema21.iloc[-1]:
            self._build_signal(choices.OrderSide.BUY)
        elif ema9.iloc[-2] > ema21.iloc[-2] and ema9.iloc[-1] < ema21.iloc[-1]:
            return self._build_signal(choices.OrderSide.SELL)
        return self._build_signal(choices.OrderSide.HOLD)
