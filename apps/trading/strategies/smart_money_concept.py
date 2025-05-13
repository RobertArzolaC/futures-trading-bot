from apps.trading import choices
from apps.trading.strategies._base import TradingStrategy


class SmartMoneyConceptStrategy(TradingStrategy):
    """
    Estrategia basada en Smart Money Concepts (SMC).
    Detecta manipulación institucional, liquidity grabs y order flow.
    Altamente efectiva en crypto para capturar movimientos institucionales.
    """

    def generate_signal(self):
        # Identificar estructura de mercado
        window = 20

        # Detectar Higher Highs (HH), Higher Lows (HL), Lower Highs (LH), Lower Lows (LL)
        highs = self.df["high"].rolling(window=5).max()
        lows = self.df["low"].rolling(window=5).min()

        # Identificar swing points
        swing_highs = []
        swing_lows = []

        for i in range(5, len(self.df) - 5):
            # Swing high: máximo local
            if (
                self.df["high"].iloc[i]
                == self.df["high"].iloc[i - 5 : i + 5].max()
            ):
                swing_highs.append(
                    {"index": i, "price": self.df["high"].iloc[i]}
                )

            # Swing low: mínimo local
            if (
                self.df["low"].iloc[i]
                == self.df["low"].iloc[i - 5 : i + 5].min()
            ):
                swing_lows.append({"index": i, "price": self.df["low"].iloc[i]})

        # Determinar tendencia basada en estructura
        trend = "neutral"
        if len(swing_highs) >= 2 and len(swing_lows) >= 2:
            last_high = swing_highs[-1]["price"]
            prev_high = swing_highs[-2]["price"]
            last_low = swing_lows[-1]["price"]
            prev_low = swing_lows[-2]["price"]

            if last_high > prev_high and last_low > prev_low:
                trend = "bullish"
            elif last_high < prev_high and last_low < prev_low:
                trend = "bearish"

        # Identificar Break of Structure (BOS) y Change of Character (ChoCH)
        current_price = self.df["close"].iloc[-1]
        prev_close = self.df["close"].iloc[-2]

        bos_bullish = False
        bos_bearish = False
        choch = False

        if swing_highs and swing_lows:
            # BOS alcista: rompe último swing high en tendencia alcista
            if trend == "bullish" and current_price > swing_highs[-1]["price"]:
                bos_bullish = True

            # BOS bajista: rompe último swing low en tendencia bajista
            if trend == "bearish" and current_price < swing_lows[-1]["price"]:
                bos_bearish = True

            # ChoCH: cambio de carácter (de alcista a bajista o viceversa)
            if trend == "bullish" and current_price < swing_lows[-1]["price"]:
                choch = True
                trend = "bearish"
            elif (
                trend == "bearish" and current_price > swing_highs[-1]["price"]
            ):
                choch = True
                trend = "bullish"

        # Identificar Liquidity Grabs (cazas de liquidez)
        liquidity_grab_long = False
        liquidity_grab_short = False

        if len(self.df) >= 3:
            # Liquidity grab largo: spike por debajo de mínimo previo y cierre por encima
            recent_low = self.df["low"].iloc[-10:-1].min()
            if (
                self.df["low"].iloc[-1] < recent_low
                and self.df["close"].iloc[-1] > recent_low
                and self.df["close"].iloc[-1] > self.df["open"].iloc[-1]
            ):
                liquidity_grab_long = True

            # Liquidity grab corto: spike por encima de máximo previo y cierre por debajo
            recent_high = self.df["high"].iloc[-10:-1].max()
            if (
                self.df["high"].iloc[-1] > recent_high
                and self.df["close"].iloc[-1] < recent_high
                and self.df["close"].iloc[-1] < self.df["open"].iloc[-1]
            ):
                liquidity_grab_short = True

        # Identificar Fair Value Gaps (FVG) / Imbalances
        fvg_bullish = []
        fvg_bearish = []

        for i in range(2, len(self.df) - 1):
            # FVG alcista: gap entre el mínimo de vela 1 y máximo de vela 3
            if self.df["low"].iloc[i - 2] > self.df["high"].iloc[i]:
                fvg_bullish.append(
                    {
                        "high": self.df["low"].iloc[i - 2],
                        "low": self.df["high"].iloc[i],
                        "index": i - 1,
                    }
                )

            # FVG bajista: gap entre el máximo de vela 1 y mínimo de vela 3
            if self.df["high"].iloc[i - 2] < self.df["low"].iloc[i]:
                fvg_bearish.append(
                    {
                        "high": self.df["low"].iloc[i],
                        "low": self.df["high"].iloc[i - 2],
                        "index": i - 1,
                    }
                )

        # Generar señales basadas en SMC

        # 1. Liquidity grab + retorno a FVG
        if liquidity_grab_long and fvg_bullish:
            # Buscar FVG cercano no rellenado
            for fvg in fvg_bullish[-3:]:
                if current_price >= fvg["low"] and current_price <= fvg["high"]:
                    return self._build_signal(choices.OrderSide.BUY)

        if liquidity_grab_short and fvg_bearish:
            # Buscar FVG cercano no rellenado
            for fvg in fvg_bearish[-3:]:
                if current_price >= fvg["low"] and current_price <= fvg["high"]:
                    return self._build_signal(choices.OrderSide.SELL)

        # 2. BOS con retracción a zona de demanda/oferta
        if bos_bullish:
            # Buscar retracción a zona de demanda (último swing low)
            if swing_lows and current_price <= swing_lows[-1]["price"] * 1.01:
                return self._build_signal(choices.OrderSide.BUY)

        if bos_bearish:
            # Buscar retracción a zona de oferta (último swing high)
            if swing_highs and current_price >= swing_highs[-1]["price"] * 0.99:
                return self._build_signal(choices.OrderSide.SELL)

        # 3. ChoCH con confirmación de volumen
        avg_volume = self.df["volume"].rolling(window=20).mean()
        if choch and self.df["volume"].iloc[-1] > avg_volume.iloc[-1] * 1.5:
            if trend == "bullish":
                return self._build_signal(choices.OrderSide.BUY)
            else:
                return self._build_signal(choices.OrderSide.SELL)

        # 4. Mitigación de Order Blocks después de BOS
        if bos_bullish and len(self.df) >= 50:
            # Buscar último order block bajista antes del BOS
            for i in range(len(self.df) - 10, max(0, len(self.df) - 50), -1):
                if (
                    self.df["close"].iloc[i] < self.df["open"].iloc[i]
                    and self.df["volume"].iloc[i] > avg_volume.iloc[i] * 1.3
                ):
                    ob_high = self.df["high"].iloc[i]
                    ob_low = self.df["low"].iloc[i]

                    # Si precio retrocede al OB
                    if (
                        current_price >= ob_low
                        and current_price <= ob_high
                        and current_price > prev_close
                    ):
                        return self._build_signal(choices.OrderSide.BUY)

        return self._build_signal(choices.OrderSide.HOLD)
