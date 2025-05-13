import ta

from apps.trading import choices
from apps.trading.strategies._base import TradingStrategy


class SqueezeMomentumStrategy(TradingStrategy):
    """
    Estrategia Squeeze Momentum Indicator (SMI).
    Detecta períodos de baja volatilidad seguidos de expansión.
    Muy efectiva en crypto para capturar movimientos explosivos.
    """

    def generate_signal(self):
        # Calcular Bollinger Bands
        bb = ta.volatility.BollingerBands(
            self.df["close"], window=20, window_dev=2
        )
        bb_upper = bb.bollinger_hband()
        bb_lower = bb.bollinger_lband()
        bb_width = bb_upper - bb_lower

        # Calcular Keltner Channels
        atr = ta.volatility.AverageTrueRange(
            self.df["high"], self.df["low"], self.df["close"], window=20
        ).average_true_range()
        ema20 = self.df["close"].ewm(span=20).mean()
        kc_upper = ema20 + (1.5 * atr)
        kc_lower = ema20 - (1.5 * atr)

        # Detectar squeeze (cuando BB está dentro de KC)
        squeeze_on = (bb_upper < kc_upper) & (bb_lower > kc_lower)

        # Momentum usando Linear Regression
        window = 20
        momentum = []

        for i in range(window, len(self.df)):
            # Calcular regresión lineal en ventana móvil
            x = list(range(window))
            y = self.df["close"].iloc[i - window : i].values

            # Cálculo manual de pendiente
            n = len(x)
            sum_x = sum(x)
            sum_y = sum(y)
            sum_xy = sum(x[j] * y[j] for j in range(n))
            sum_x2 = sum(x[j] ** 2 for j in range(n))

            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x**2)
            momentum.append(slope)

        # Agregar valores iniciales para mantener longitud
        momentum = [0] * window + momentum

        # Condiciones de trading
        if len(squeeze_on) >= 3:
            # Salida del squeeze con momentum positivo
            if (
                squeeze_on.iloc[-3] == True
                and squeeze_on.iloc[-2] == True
                and squeeze_on.iloc[-1] == False
                and momentum[-1] > 0
            ):
                return self._build_signal(choices.OrderSide.BUY)

            # Salida del squeeze con momentum negativo
            elif (
                squeeze_on.iloc[-3] == True
                and squeeze_on.iloc[-2] == True
                and squeeze_on.iloc[-1] == False
                and momentum[-1] < 0
            ):
                return self._build_signal(choices.OrderSide.SELL)

        # Señales adicionales basadas en momentum extremo
        if len(momentum) >= 10:
            momentum_avg = sum(momentum[-10:]) / 10

            # Momentum muy positivo
            if momentum[-1] > momentum_avg * 2 and momentum[-2] < momentum[-1]:
                return self._build_signal(choices.OrderSide.BUY)

            # Momentum muy negativo
            elif (
                momentum[-1] < -momentum_avg * 2 and momentum[-2] > momentum[-1]
            ):
                return self._build_signal(choices.OrderSide.SELL)

        return self._build_signal(choices.OrderSide.HOLD)
