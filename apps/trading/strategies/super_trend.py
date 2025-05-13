import ta

from apps.trading import choices
from apps.trading.strategies._base import TradingStrategy


class SupertrendStrategy(TradingStrategy):
    """
    Estrategia Supertrend - muy popular en crypto por su capacidad
    de seguir tendencias fuertes y filtrar ruido del mercado.
    Excelente para mercados trending de Bitcoin y altcoins.
    """

    def generate_signal(self):
        # Calcular ATR (Average True Range)
        atr = ta.volatility.AverageTrueRange(
            high=self.df["high"],
            low=self.df["low"],
            close=self.df["close"],
            window=10,
        )
        atr_values = atr.average_true_range()

        # Parámetros de Supertrend
        multiplier = 2.5
        hl2 = (self.df["high"] + self.df["low"]) / 2

        # Calcular bandas superiores e inferiores
        up = hl2 - (multiplier * atr_values)
        dn = hl2 + (multiplier * atr_values)

        # Calcular Supertrend
        supertrend = [0] * len(self.df)
        direction = [1] * len(self.df)  # 1 = up, -1 = down

        for i in range(1, len(self.df)):
            # Actualizar bandas
            if (
                up.iloc[i] > supertrend[i - 1]
                or self.df["close"].iloc[i - 1] <= supertrend[i - 1]
            ):
                up.iloc[i] = up.iloc[i]
            else:
                up.iloc[i] = supertrend[i - 1]

            if (
                dn.iloc[i] < supertrend[i - 1]
                or self.df["close"].iloc[i - 1] >= supertrend[i - 1]
            ):
                dn.iloc[i] = dn.iloc[i]
            else:
                dn.iloc[i] = supertrend[i - 1]

            # Determinar dirección
            if self.df["close"].iloc[i] <= dn.iloc[i]:
                direction[i] = -1
            elif self.df["close"].iloc[i] >= up.iloc[i]:
                direction[i] = 1
            else:
                direction[i] = direction[i - 1]

            # Asignar valor de Supertrend
            if direction[i] == 1:
                supertrend[i] = up.iloc[i]
            else:
                supertrend[i] = dn.iloc[i]

        # Generar señales basadas en cambios de dirección
        if direction[-2] == -1 and direction[-1] == 1:
            return self._build_signal(choices.OrderSide.BUY)
        elif direction[-2] == 1 and direction[-1] == -1:
            return self._build_signal(choices.OrderSide.SELL)

        return self._build_signal(choices.OrderSide.HOLD)
