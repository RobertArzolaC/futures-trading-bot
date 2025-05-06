from abc import ABC, abstractmethod

import pandas as pd


class TradingStrategy(ABC):
    def __init__(self, data: pd.DataFrame, symbol: str, timeframe: str):
        self.df = data
        self.symbol = symbol
        self.timeframe = timeframe

    @abstractmethod
    def generate_signal(self):
        pass

    def _build_signal(self, signal):
        return {
            "ticker": self.symbol,
            "signal": signal,
            "timeframe": self.timeframe,
            "strategy": self.__class__.__name__,
            "price_close": float(self.df["close"].iloc[-1]),
        }
