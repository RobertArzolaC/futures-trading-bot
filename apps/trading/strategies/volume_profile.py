import numpy as np

from apps.trading import choices
from apps.trading.strategies._base import TradingStrategy


class VolumeProfileStrategy(TradingStrategy):
    def generate_signal(self):
        # Definir número de divisiones de precio (POC = Point of Control)
        num_bins = 20

        # Calcular rango de precios en el período analizado
        price_min = self.df["low"].min()
        price_max = self.df["high"].max()
        price_bins = np.linspace(price_min, price_max, num_bins + 1)

        # Construir perfil de volumen
        volume_profile = np.zeros(num_bins)
        for i in range(len(self.df)):
            price = self.df["close"].iloc[i]
            volume = self.df["volume"].iloc[i]

            # Determinar en qué división cae el precio
            bin_index = int(np.digitize(price, price_bins) - 1)
            if 0 <= bin_index < num_bins:
                volume_profile[bin_index] += volume

        # Encontrar POC (Point of Control) - nivel con mayor volumen
        poc_index = np.argmax(volume_profile)
        poc_price = (price_bins[poc_index] + price_bins[poc_index + 1]) / 2

        # Obtener precio actual
        current_price = self.df["close"].iloc[-1]
        previous_price = self.df["close"].iloc[-2]

        # Generar señales basadas en la relación con el POC
        distance_to_poc = abs(current_price - poc_price) / poc_price

        # Si estamos muy por debajo del POC y el precio está subiendo, comprar
        if (
            current_price < poc_price
            and current_price > previous_price
            and distance_to_poc > 0.02
        ):
            return self._build_signal(choices.OrderSide.BUY)

        # Si estamos muy por encima del POC y el precio está bajando, vender
        elif (
            current_price > poc_price
            and current_price < previous_price
            and distance_to_poc > 0.02
        ):
            return self._build_signal(choices.OrderSide.SELL)

        return self._build_signal(choices.OrderSide.HOLD)
