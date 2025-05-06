import ta

from apps.trading import choices
from apps.trading.strategies._base import TradingStrategy


class ADXTrendStrategy(TradingStrategy):
    def generate_signal(self):
        adx = ta.trend.ADXIndicator(
            self.df["high"], self.df["low"], self.df["close"], window=14
        )
        self.df["adx"] = adx.adx()
        ema_short = self.df["close"].ewm(span=9).mean()
        ema_long = self.df["close"].ewm(span=21).mean()

        if self.df["adx"].iloc[-1] > 25:
            if (
                ema_short.iloc[-2] < ema_long.iloc[-2]
                and ema_short.iloc[-1] > ema_long.iloc[-1]
            ):
                return self._build_signal(choices.OrderSide.BUY)
            elif (
                ema_short.iloc[-2] > ema_long.iloc[-2]
                and ema_short.iloc[-1] < ema_long.iloc[-1]
            ):
                return self._build_signal(choices.OrderSide.SELL)
        return self._build_signal(choices.OrderSide.HOLD)
