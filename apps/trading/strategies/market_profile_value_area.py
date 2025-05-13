import numpy as np

from apps.trading import choices
from apps.trading.strategies._base import TradingStrategy


class MarketProfileVAStrategy(TradingStrategy):
    """
    Estrategia basada en Market Profile y Value Area (VA).
    Identifica zonas de alto valor donde el precio pasa más tiempo.
    Extremadamente efectiva en crypto para day trading y scalping.
    """

    def generate_signal(self):
        # Calcular TPO (Time Price Opportunity) simplificado
        window = 30  # Período para calcular el perfil

        # Dividir el rango de precios en bins
        price_min = self.df["low"].iloc[-window:].min()
        price_max = self.df["high"].iloc[-window:].max()

        # Crear 30 niveles de precio
        num_levels = 30
        price_levels = np.linspace(price_min, price_max, num_levels)

        # Calcular tiempo en cada nivel (TPO)
        tpo_profile = np.zeros(num_levels - 1)

        for i in range(len(self.df) - window, len(self.df)):
            high = self.df["high"].iloc[i]
            low = self.df["low"].iloc[i]

            # Encontrar qué niveles toca esta vela
            for j in range(num_levels - 1):
                if low <= price_levels[j + 1] and high >= price_levels[j]:
                    tpo_profile[j] += 1

        # Calcular Value Area (70% del volumen)
        total_tpo = np.sum(tpo_profile)
        target_tpo = total_tpo * 0.7

        # Encontrar POC (Point of Control)
        poc_index = np.argmax(tpo_profile)
        poc_price = (price_levels[poc_index] + price_levels[poc_index + 1]) / 2

        # Expandir desde POC para encontrar Value Area
        va_indices = [poc_index]
        current_tpo = tpo_profile[poc_index]

        while current_tpo < target_tpo:
            # Buscar siguiente nivel con más TPO
            left_idx = va_indices[0] - 1 if va_indices[0] > 0 else -1
            right_idx = (
                va_indices[-1] + 1
                if va_indices[-1] < len(tpo_profile) - 1
                else -1
            )

            left_tpo = tpo_profile[left_idx] if left_idx >= 0 else 0
            right_tpo = tpo_profile[right_idx] if right_idx >= 0 else 0

            if left_tpo >= right_tpo and left_idx >= 0:
                va_indices.insert(0, left_idx)
                current_tpo += left_tpo
            elif right_idx >= 0:
                va_indices.append(right_idx)
                current_tpo += right_tpo
            else:
                break

        # Definir Value Area High (VAH) y Value Area Low (VAL)
        val_price = (
            price_levels[va_indices[0]] + price_levels[va_indices[0] + 1]
        ) / 2
        vah_price = (
            price_levels[va_indices[-1]] + price_levels[va_indices[-1] + 1]
        ) / 2

        # Precio actual y dirección
        current_price = self.df["close"].iloc[-1]
        prev_price = self.df["close"].iloc[-2]

        # VWAP para confirmar dirección
        typical_price = (
            self.df["high"] + self.df["low"] + self.df["close"]
        ) / 3
        vwap = (typical_price * self.df["volume"]).sum() / self.df[
            "volume"
        ].sum()

        # Generar señales basadas en Market Profile

        # 1. Bounces desde VAL (soporte del Value Area)
        if (
            prev_price > val_price
            and self.df["low"].iloc[-1] <= val_price
            and current_price > val_price
            and current_price > prev_price
        ):
            return self._build_signal(choices.OrderSide.BUY)

        # 2. Rechazo desde VAH (resistencia del Value Area)
        if (
            prev_price < vah_price
            and self.df["high"].iloc[-1] >= vah_price
            and current_price < vah_price
            and current_price < prev_price
        ):
            return self._build_signal(choices.OrderSide.SELL)

        # 3. Breakout del Value Area con volumen
        avg_volume = self.df["volume"].rolling(window=20).mean()
        high_volume = self.df["volume"].iloc[-1] > avg_volume.iloc[-1] * 1.5

        if prev_price < vah_price and current_price > vah_price and high_volume:
            return self._build_signal(choices.OrderSide.BUY)

        if prev_price > val_price and current_price < val_price and high_volume:
            return self._build_signal(choices.OrderSide.SELL)

        # 4. Mean reversion hacia POC
        distance_to_poc = abs(current_price - poc_price) / poc_price

        # Si está muy lejos del POC y volviendo hacia él
        if distance_to_poc > 0.02:  # Más de 2% de distancia
            if current_price > poc_price and current_price < prev_price:
                # Precio sobre POC y bajando hacia él
                return self._build_signal(choices.OrderSide.SELL)
            elif current_price < poc_price and current_price > prev_price:
                # Precio bajo POC y subiendo hacia él
                return self._build_signal(choices.OrderSide.BUY)

        # 5. Operaciones en los extremos del perfil
        profile_high = price_levels[-1]
        profile_low = price_levels[0]

        # Compra en extremo inferior con reversión
        if (
            current_price <= profile_low * 1.01
            and current_price > prev_price
            and self.df["volume"].iloc[-1] > avg_volume.iloc[-1]
        ):
            return self._build_signal(choices.OrderSide.BUY)

        # Venta en extremo superior con reversión
        if (
            current_price >= profile_high * 0.99
            and current_price < prev_price
            and self.df["volume"].iloc[-1] > avg_volume.iloc[-1]
        ):
            return self._build_signal(choices.OrderSide.SELL)

        return self._build_signal(choices.OrderSide.HOLD)
