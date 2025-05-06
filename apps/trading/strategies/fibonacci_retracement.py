from apps.trading import choices
from apps.trading.strategies._base import TradingStrategy


class FibonacciRetracementStrategy(TradingStrategy):
    def generate_signal(self):
        # Identificar tendencia reciente (últimas 30 velas)
        window = 30

        if len(self.df) < window:
            return self._build_signal(choices.OrderSide.HOLD)

        recent_df = self.df.iloc[-window:]

        # Encontrar swing high y swing low
        swing_high = recent_df["high"].max()
        swing_low = recent_df["low"].min()

        # Definir niveles de Fibonacci comunes
        fib_levels = {
            0: swing_low,
            0.236: swing_low + 0.236 * (swing_high - swing_low),
            0.382: swing_low + 0.382 * (swing_high - swing_low),
            0.5: swing_low + 0.5 * (swing_high - swing_low),
            0.618: swing_low + 0.618 * (swing_high - swing_low),
            0.786: swing_low + 0.786 * (swing_high - swing_low),
            1: swing_high,
        }

        current_price = self.df["close"].iloc[-1]
        prev_price = self.df["close"].iloc[-2]

        # Determinar tendencia
        uptrend = recent_df["close"].iloc[-1] > recent_df["close"].iloc[0]

        # En tendencia alcista, comprar en retrocesos a niveles de soporte Fibonacci
        if uptrend:
            for level in [0.618, 0.5, 0.382]:
                fib_price = fib_levels[level]
                # Si el precio ha retrocedido hasta este nivel y ahora está rebotando
                if prev_price <= fib_price and current_price > fib_price:
                    return self._build_signal(choices.OrderSide.BUY)

        # En tendencia bajista, vender en rebotes a niveles de resistencia Fibonacci
        else:
            for level in [0.382, 0.5, 0.618]:
                fib_price = fib_levels[level]
                # Si el precio ha rebotado hasta este nivel y ahora está retrocediendo
                if prev_price >= fib_price and current_price < fib_price:
                    return self._build_signal(choices.OrderSide.SELL)

        return self._build_signal(choices.OrderSide.HOLD)
