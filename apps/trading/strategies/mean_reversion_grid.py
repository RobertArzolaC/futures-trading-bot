from apps.trading import choices
from apps.trading.strategies._base import TradingStrategy


class MeanReversionGridStrategy(TradingStrategy):
    """
    Estrategia de reversión a la media con niveles de grid.
    Popular en crypto para mercados laterales o con alta volatilidad.
    Compra en niveles de soporte y vende en resistencia.
    """

    def generate_signal(self):
        # Calcular media móvil simple de 50 períodos
        sma50 = self.df["close"].rolling(window=50).mean()

        # Calcular desviación estándar para determinar la volatilidad
        std_dev = self.df["close"].rolling(window=20).std()

        current_price = self.df["close"].iloc[-1]
        mean_price = sma50.iloc[-1]
        current_std = std_dev.iloc[-1]

        # Definir niveles de grid basados en desviación estándar
        grid_levels = {
            "extreme_oversold": mean_price - 2.5 * current_std,
            "oversold": mean_price - 1.5 * current_std,
            "slightly_oversold": mean_price - 0.75 * current_std,
            "mean": mean_price,
            "slightly_overbought": mean_price + 0.75 * current_std,
            "overbought": mean_price + 1.5 * current_std,
            "extreme_overbought": mean_price + 2.5 * current_std,
        }

        # Calcular distancia del precio actual a la media
        distance_from_mean = (current_price - mean_price) / mean_price

        # Señales de compra en niveles de soporte
        if current_price <= grid_levels["extreme_oversold"]:
            return self._build_signal(choices.OrderSide.BUY)
        elif (
            current_price <= grid_levels["oversold"]
            and distance_from_mean < -0.03
        ):
            return self._build_signal(choices.OrderSide.BUY)

        # Señales de venta en niveles de resistencia
        elif current_price >= grid_levels["extreme_overbought"]:
            return self._build_signal(choices.OrderSide.SELL)
        elif (
            current_price >= grid_levels["overbought"]
            and distance_from_mean > 0.03
        ):
            return self._build_signal(choices.OrderSide.SELL)

        return self._build_signal(choices.OrderSide.HOLD)
