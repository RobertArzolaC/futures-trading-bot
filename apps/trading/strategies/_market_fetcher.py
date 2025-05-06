import ccxt
import pandas as pd


class MarketDataFetcher:
    def __init__(self, symbol, timeframe="1h", limit=100):
        self.symbol = symbol
        self.timeframe = timeframe
        self.limit = limit
        self.exchange = ccxt.binance()

    def fetch(self) -> pd.DataFrame:
        ohlcv = self.exchange.fetch_ohlcv(
            self.symbol, timeframe=self.timeframe, limit=self.limit
        )
        df = pd.DataFrame(
            ohlcv,
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df
