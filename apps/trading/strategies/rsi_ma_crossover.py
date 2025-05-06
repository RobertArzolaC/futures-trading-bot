import ta

from apps.trading import choices
from apps.trading.strategies._base import TradingStrategy


class RSIMACrossoverStrategy(TradingStrategy):
    def generate_signal(self) -> str:
        self.df["rsi"] = ta.momentum.RSIIndicator(
            self.df["close"], window=14
        ).rsi()
        ema_short = self.df["close"].ewm(span=9).mean()
        ema_long = self.df["close"].ewm(span=21).mean()

        if (
            self.df["rsi"].iloc[-1] < 30
            and ema_short.iloc[-2] < ema_long.iloc[-2]
            and ema_short.iloc[-1] > ema_long.iloc[-1]
        ):
            return self._build_signal(choices.OrderSide.BUY)
        elif (
            self.df["rsi"].iloc[-1] > 70
            and ema_short.iloc[-2] > ema_long.iloc[-2]
            and ema_short.iloc[-1] < ema_long.iloc[-1]
        ):
            return self._build_signal(choices.OrderSide.SELL)
        return self._build_signal(choices.OrderSide.HOLD)
