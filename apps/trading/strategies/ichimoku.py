import ta

from apps.trading import choices
from apps.trading.strategies._base import TradingStrategy


class IchimokuStrategy(TradingStrategy):
    def generate_signal(self):
        # Calcular componentes de Ichimoku
        ichimoku = ta.trend.IchimokuIndicator(
            high=self.df["high"],
            low=self.df["low"],
            window1=9,  # Tenkan-sen (línea de conversión)
            window2=26,  # Kijun-sen (línea base)
            window3=52,  # Chikou-span (línea de retraso)
        )

        self.df["tenkan_sen"] = ichimoku.ichimoku_conversion_line()
        self.df["kijun_sen"] = ichimoku.ichimoku_base_line()
        self.df["senkou_span_a"] = ichimoku.ichimoku_a()
        self.df["senkou_span_b"] = ichimoku.ichimoku_b()

        price = self.df["close"].iloc[-1]
        tenkan = self.df["tenkan_sen"].iloc[-1]
        kijun = self.df["kijun_sen"].iloc[-1]
        span_a = self.df["senkou_span_a"].iloc[-1]
        span_b = self.df["senkou_span_b"].iloc[-1]

        # Condiciones de compra
        if (
            tenkan > kijun
            and price > span_a
            and price > span_b
            and self.df["tenkan_sen"].iloc[-2] <= self.df["kijun_sen"].iloc[-2]
        ):
            return self._build_signal(choices.OrderSide.BUY)

        # Condiciones de venta
        elif (
            tenkan < kijun
            and price < span_a
            and price < span_b
            and self.df["tenkan_sen"].iloc[-2] >= self.df["kijun_sen"].iloc[-2]
        ):
            return self._build_signal(choices.OrderSide.SELL)

        return self._build_signal(choices.OrderSide.HOLD)
