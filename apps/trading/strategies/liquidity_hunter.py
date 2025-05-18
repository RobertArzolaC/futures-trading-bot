import ta

from apps.trading import choices
from apps.trading.strategies._base import TradingStrategy


class LiquidityHunterStrategy(TradingStrategy):
    """
    Estrategia de caza de liquidez para timeframes de 15 minutos.
    Se enfoca en detectar stops liquidity hunts, manipulaciones institucionales y
    aprovecha los fake breakouts para entrar en la dirección correcta.
    Altamente rentable en mercados de crypto de alta liquidez.
    """

    def generate_signal(self):
        # Ventana para analizar swings y liquidez
        window = 30  # 7.5 horas en timeframe de 15 min

        # Series de datos
        open_prices = self.df["open"]
        high_prices = self.df["high"]
        low_prices = self.df["low"]
        close_prices = self.df["close"]
        volumes = self.df["volume"]

        # --- Identificación de niveles de liquidez ---

        # 1. Detectar swings (puntos de giro)
        # Usando una ventana móvil para identificar picos y valles locales
        swing_highs = []
        swing_lows = []

        for i in range(3, len(self.df) - 3):
            # Swing high: cuando una vela tiene máximo mayor que las 3 velas antes y después
            if high_prices.iloc[i] == high_prices.iloc[i - 3 : i + 4].max():
                swing_highs.append(
                    {
                        "index": i,
                        "price": high_prices.iloc[i],
                        "volume": volumes.iloc[i],
                    }
                )

            # Swing low: cuando una vela tiene mínimo menor que las 3 velas antes y después
            if low_prices.iloc[i] == low_prices.iloc[i - 3 : i + 4].min():
                swing_lows.append(
                    {
                        "index": i,
                        "price": low_prices.iloc[i],
                        "volume": volumes.iloc[i],
                    }
                )

        # Filtrar solo los swings recientes (últimas window velas)
        recent_highs = [
            h for h in swing_highs if h["index"] >= len(self.df) - window
        ]
        recent_lows = [
            l for l in swing_lows if l["index"] >= len(self.df) - window
        ]

        # 2. Identificar zonas de liquidez (clusters de swing points)
        def group_levels(levels, threshold=0.003):
            if not levels:
                return []

            # Ordenar niveles por precio
            sorted_levels = sorted(levels, key=lambda x: x["price"])

            # Agrupar niveles similares
            groups = []
            current_group = [sorted_levels[0]]

            for i in range(1, len(sorted_levels)):
                price_diff = (
                    abs(sorted_levels[i]["price"] - current_group[-1]["price"])
                    / current_group[-1]["price"]
                )

                if price_diff <= threshold:
                    current_group.append(sorted_levels[i])
                else:
                    # Consolidar grupo actual y comenzar uno nuevo
                    avg_price = sum(l["price"] for l in current_group) / len(
                        current_group
                    )
                    total_volume = sum(l["volume"] for l in current_group)
                    groups.append(
                        {
                            "price": avg_price,
                            "volume": total_volume,
                            "count": len(current_group),
                        }
                    )
                    current_group = [sorted_levels[i]]

            # Añadir último grupo
            if current_group:
                avg_price = sum(l["price"] for l in current_group) / len(
                    current_group
                )
                total_volume = sum(l["volume"] for l in current_group)
                groups.append(
                    {
                        "price": avg_price,
                        "volume": total_volume,
                        "count": len(current_group),
                    }
                )

            return groups

        # Crear clusters de liquidez
        high_liquidity_zones = group_levels(recent_highs)
        low_liquidity_zones = group_levels(recent_lows)

        # Ordenar por importancia (# de swings y volumen)
        high_liquidity_zones = sorted(
            high_liquidity_zones,
            key=lambda x: (x["count"], x["volume"]),
            reverse=True,
        )

        low_liquidity_zones = sorted(
            low_liquidity_zones,
            key=lambda x: (x["count"], x["volume"]),
            reverse=True,
        )

        # 3. ATR y volatilidad para determinar penetración de niveles
        atr = ta.volatility.AverageTrueRange(
            high=high_prices, low=low_prices, close=close_prices, window=14
        ).average_true_range()

        current_atr = atr.iloc[-1]

        # --- Detección de cazas de liquidez ---

        # Precios actuales
        current_price = close_prices.iloc[-1]
        current_high = high_prices.iloc[-1]
        current_low = low_prices.iloc[-1]
        prev_close = close_prices.iloc[-2]

        # Señales de caza de liquidez
        liquidity_hunt_buy = False
        liquidity_hunt_sell = False

        # 1. Falso breakout inferior (caza de stops de cortos)
        for zone in low_liquidity_zones[
            :3
        ]:  # Revisar las 3 zonas más importantes
            # Si el precio penetró brevemente el nivel pero cerró por encima
            penetration = (
                current_low
                < zone["price"] * 0.995  # Penetración de al menos 0.5%
                and current_price > zone["price"] * 1.002  # Cierra por encima
                and current_price > prev_close
            )  # Cierre alcista

            # Confirmar con volumen
            vol_confirm = volumes.iloc[-1] > volumes.iloc[-5:].mean() * 1.3

            if penetration and vol_confirm:
                liquidity_hunt_buy = True
                break

        # 2. Falso breakout superior (caza de stops de largos)
        for zone in high_liquidity_zones[
            :3
        ]:  # Revisar las 3 zonas más importantes
            # Si el precio penetró brevemente el nivel pero cerró por debajo
            penetration = (
                current_high
                > zone["price"] * 1.005  # Penetración de al menos 0.5%
                and current_price < zone["price"] * 0.998  # Cierra por debajo
                and current_price < prev_close
            )  # Cierre bajista

            # Confirmar con volumen
            vol_confirm = volumes.iloc[-1] > volumes.iloc[-5:].mean() * 1.3

            if penetration and vol_confirm:
                liquidity_hunt_sell = True
                break

        # --- Análisis adicional de market structure ---

        # 1. Detectar cambio de estructura (BOS - Break of Structure)
        # Últimos 3 swing highs y lows para analizar estructura
        recent_swing_high_prices = (
            [h["price"] for h in recent_highs[-3:]]
            if len(recent_highs) >= 3
            else []
        )
        recent_swing_low_prices = (
            [l["price"] for l in recent_lows[-3:]]
            if len(recent_lows) >= 3
            else []
        )

        # Estructura alcista: higher highs, higher lows
        bullish_structure = (
            len(recent_swing_high_prices) >= 2
            and len(recent_swing_low_prices) >= 2
            and recent_swing_high_prices[-1] > recent_swing_high_prices[-2]
            and recent_swing_low_prices[-1] > recent_swing_low_prices[-2]
        )

        # Estructura bajista: lower highs, lower lows
        bearish_structure = (
            len(recent_swing_high_prices) >= 2
            and len(recent_swing_low_prices) >= 2
            and recent_swing_high_prices[-1] < recent_swing_high_prices[-2]
            and recent_swing_low_prices[-1] < recent_swing_low_prices[-2]
        )

        # 2. VWAP como referencia institucional
        typical_price = (high_prices + low_prices + close_prices) / 3
        vwap = (typical_price * volumes).cumsum() / volumes.cumsum()

        # 3. Order Flow - Indicador de fuerza
        buy_pressure = (
            (close_prices - low_prices) / (high_prices - low_prices + 0.000001)
        ) * volumes
        sell_pressure = (
            (high_prices - close_prices) / (high_prices - low_prices + 0.000001)
        ) * volumes

        # Cumulative Delta
        delta = buy_pressure - sell_pressure
        cumulative_delta = delta.rolling(10).sum()

        # --- Generación de señales ---

        # Combinar todas las señales
        buy_conditions = [
            # Caza de liquidez alcista confirmada
            liquidity_hunt_buy,
            # Rebote fuerte en zona de liquidez baja
            any(
                abs(current_low - zone["price"]) / zone["price"] < 0.002
                and current_price > prev_close
                and current_price > (current_low + current_high) / 2
                for zone in low_liquidity_zones[:2]
            ),
            # Estructura alcista con confirmación de orden flow
            (
                bullish_structure
                and cumulative_delta.iloc[-1] > 0
                and current_price > vwap.iloc[-1]
                and volumes.iloc[-1] > volumes.iloc[-5:].mean()
            ),
        ]

        sell_conditions = [
            # Caza de liquidez bajista confirmada
            liquidity_hunt_sell,
            # Rechazo fuerte en zona de liquidez alta
            any(
                abs(current_high - zone["price"]) / zone["price"] < 0.002
                and current_price < prev_close
                and current_price < (current_low + current_high) / 2
                for zone in high_liquidity_zones[:2]
            ),
            # Estructura bajista con confirmación de orden flow
            (
                bearish_structure
                and cumulative_delta.iloc[-1] < 0
                and current_price < vwap.iloc[-1]
                and volumes.iloc[-1] > volumes.iloc[-5:].mean()
            ),
        ]

        # Generar señal final
        if any(buy_conditions):
            return self._build_signal(choices.OrderSide.BUY)
        elif any(sell_conditions):
            return self._build_signal(choices.OrderSide.SELL)

        return self._build_signal(choices.OrderSide.HOLD)
