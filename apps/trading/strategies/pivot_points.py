from apps.trading import choices
from apps.trading.strategies._base import TradingStrategy


class PivotPointsStrategy(TradingStrategy):
    def generate_signal(self):
        # Obtener datos del día anterior o periodo anterior
        if len(self.df) < 2:
            return self._build_signal(choices.OrderSide.HOLD)

        prev_high = self.df["high"].iloc[-2]
        prev_low = self.df["low"].iloc[-2]
        prev_close = self.df["close"].iloc[-2]

        # Calcular pivot point y niveles de soporte/resistencia
        pivot = (prev_high + prev_low + prev_close) / 3

        r1 = 2 * pivot - prev_low
        r2 = pivot + (prev_high - prev_low)
        r3 = prev_high + 2 * (pivot - prev_low)

        s1 = 2 * pivot - prev_high
        s2 = pivot - (prev_high - prev_low)
        s3 = prev_low - 2 * (prev_high - pivot)

        current_price = self.df["close"].iloc[-1]

        # Comprar cerca de soportes, vender cerca de resistencias
        if current_price <= s1 and current_price > s2:
            return self._build_signal(choices.OrderSide.BUY)
        elif current_price <= s2 and current_price > s3:
            return self._build_signal(choices.OrderSide.BUY)

        elif current_price >= r1 and current_price < r2:
            return self._build_signal(choices.OrderSide.SELL)
        elif current_price >= r2 and current_price < r3:
            return self._build_signal(choices.OrderSide.SELL)

        return self._build_signal(choices.OrderSide.HOLD)
