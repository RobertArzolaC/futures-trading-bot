from apps.trading import choices
from apps.trading.strategies._base import TradingStrategy


class OrderBlockStrategy(TradingStrategy):
    """
    Estrategia basada en Order Blocks institucionales.
    Identifica zonas donde las instituciones han acumulado órdenes.
    Muy efectiva en crypto para detectar niveles clave de soporte/resistencia.
    """

    def generate_signal(self):
        # Identificar Order Blocks (OB)
        window = 20

        # Detectar movimientos impulsivos (indica orden institucional)
        price_change = self.df["close"].pct_change()
        volume_change = self.df["volume"].pct_change()

        # Identificar velas con movimiento fuerte y volumen alto
        impulse_threshold = 0.02  # 2% de movimiento
        volume_threshold = 1.5  # 50% más volumen que el promedio

        avg_volume = self.df["volume"].rolling(window=20).mean()

        # Marcar velas impulsivas
        bullish_impulse = (price_change > impulse_threshold) & (
            self.df["volume"] > avg_volume * volume_threshold
        )

        bearish_impulse = (price_change < -impulse_threshold) & (
            self.df["volume"] > avg_volume * volume_threshold
        )

        # Identificar Order Blocks (última vela antes del impulso)
        order_blocks = []
        for i in range(1, len(self.df)):
            if bullish_impulse.iloc[i] and i > 0:
                # OB alcista: última vela bajista antes del impulso
                if self.df["close"].iloc[i - 1] < self.df["open"].iloc[i - 1]:
                    order_blocks.append(
                        {
                            "type": "bullish",
                            "high": self.df["high"].iloc[i - 1],
                            "low": self.df["low"].iloc[i - 1],
                            "index": i - 1,
                            "strength": price_change.iloc[i],
                        }
                    )

            elif bearish_impulse.iloc[i] and i > 0:
                # OB bajista: última vela alcista antes del impulso
                if self.df["close"].iloc[i - 1] > self.df["open"].iloc[i - 1]:
                    order_blocks.append(
                        {
                            "type": "bearish",
                            "high": self.df["high"].iloc[i - 1],
                            "low": self.df["low"].iloc[i - 1],
                            "index": i - 1,
                            "strength": abs(price_change.iloc[i]),
                        }
                    )

        # Filtrar Order Blocks válidos (no tocados)
        current_price = self.df["close"].iloc[-1]
        valid_bullish_ob = []
        valid_bearish_ob = []

        for ob in order_blocks:
            # Verificar si el OB ha sido respetado (no completamente atravesado)
            if ob["type"] == "bullish":
                # Verificar si el precio no ha cerrado por debajo del OB
                violated = False
                for j in range(ob["index"] + 1, len(self.df)):
                    if self.df["close"].iloc[j] < ob["low"]:
                        violated = True
                        break

                if not violated and current_price > ob["low"]:
                    valid_bullish_ob.append(ob)

            else:  # bearish
                # Verificar si el precio no ha cerrado por encima del OB
                violated = False
                for j in range(ob["index"] + 1, len(self.df)):
                    if self.df["close"].iloc[j] > ob["high"]:
                        violated = True
                        break

                if not violated and current_price < ob["high"]:
                    valid_bearish_ob.append(ob)

        # Generar señales basadas en interacción con Order Blocks
        for ob in valid_bullish_ob[-3:]:  # Últimos 3 OB alcistas
            # Si el precio toca el OB y rebota
            if (
                self.df["low"].iloc[-1] <= ob["high"]
                and self.df["close"].iloc[-1] > ob["low"]
                and self.df["close"].iloc[-1] > self.df["open"].iloc[-1]
            ):
                # Confirmar con volumen
                if self.df["volume"].iloc[-1] > avg_volume.iloc[-1]:
                    return self._build_signal(choices.OrderSide.BUY)

        for ob in valid_bearish_ob[-3:]:  # Últimos 3 OB bajistas
            # Si el precio toca el OB y es rechazado
            if (
                self.df["high"].iloc[-1] >= ob["low"]
                and self.df["close"].iloc[-1] < ob["high"]
                and self.df["close"].iloc[-1] < self.df["open"].iloc[-1]
            ):
                # Confirmar con volumen
                if self.df["volume"].iloc[-1] > avg_volume.iloc[-1]:
                    return self._build_signal(choices.OrderSide.SELL)

        # Señales adicionales por rompimiento de OB con volumen
        if valid_bullish_ob:
            nearest_ob = min(
                valid_bullish_ob, key=lambda x: abs(current_price - x["high"])
            )
            if (
                current_price > nearest_ob["high"]
                and self.df["close"].iloc[-2] <= nearest_ob["high"]
                and self.df["volume"].iloc[-1] > avg_volume.iloc[-1] * 2
            ):
                return self._build_signal(choices.OrderSide.BUY)

        if valid_bearish_ob:
            nearest_ob = min(
                valid_bearish_ob, key=lambda x: abs(current_price - x["low"])
            )
            if (
                current_price < nearest_ob["low"]
                and self.df["close"].iloc[-2] >= nearest_ob["low"]
                and self.df["volume"].iloc[-1] > avg_volume.iloc[-1] * 2
            ):
                return self._build_signal(choices.OrderSide.SELL)

        return self._build_signal(choices.OrderSide.HOLD)
