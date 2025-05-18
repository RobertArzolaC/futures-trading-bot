import numpy as np
import pandas as pd
import ta

from apps.trading import choices
from apps.trading.strategies._base import TradingStrategy


class SupportResistanceZoneStrategy(TradingStrategy):
    """
    Estrategia basada en zonas de soporte y resistencia para timeframes de 15 minutos.
    Identifica zonas de alto volumen y reacción, utilizando price action para entradas precisas.
    Efectiva para operaciones swing en crypto y trading intradía.
    """

    def generate_signal(self):
        # Datos de precio
        open_prices = self.df["open"]
        high_prices = self.df["high"]
        low_prices = self.df["low"]
        close_prices = self.df["close"]
        volumes = self.df["volume"]

        # Parámetros optimizados para 15 minutos
        lookback_long = 240  # 60 horas - para SR histórico
        lookback_mid = 96  # 24 horas - para SR reciente
        lookback_short = 16  # 4 horas - para SR inmediato

        # --- Identificación de zonas SR ---

        # 1. Fractals para detectar swing highs/lows
        def find_fractals(high, low, n=2):
            """
            Encuentra fractals (swing highs y swing lows) en los datos de precio.
            Para n=2, examina 2 velas antes y después del punto.
            """
            bearish_fractals = np.zeros(len(high))
            bullish_fractals = np.zeros(len(low))

            for i in range(n, len(high) - n):
                # Bearish fractal (swing high)
                if high.iloc[i] == high.iloc[i - n : i + n + 1].max():
                    bearish_fractals[i] = 1

                # Bullish fractal (swing low)
                if low.iloc[i] == low.iloc[i - n : i + n + 1].min():
                    bullish_fractals[i] = 1

            return pd.Series(bearish_fractals, index=high.index), pd.Series(
                bullish_fractals, index=low.index
            )

        # Detectar fractals con diferentes configuraciones para multi-timeframe
        bf_short, bl_short = find_fractals(high_prices, low_prices, n=2)
        bf_mid, bl_mid = find_fractals(high_prices, low_prices, n=4)

        # 2. Identificar zonas de precio con fractals agrupados
        def identify_zones(fractals, prices, window=0.005):
            """
            Agrupa fractals cercanos en zonas de precio.
            window es un porcentaje del precio promedio.
            """
            zones = []
            fractal_indices = np.where(fractals == 1)[0]

            if len(fractal_indices) == 0:
                return zones

            mean_price = prices.mean()
            threshold = mean_price * window

            current_zone = {
                "min_price": float("inf"),
                "max_price": 0,
                "hits": 0,
                "indices": [],
            }

            for idx in fractal_indices:
                price = prices.iloc[idx]

                # Si el precio está dentro del umbral de la zona actual
                if (
                    abs(price - current_zone["min_price"]) < threshold
                    or abs(price - current_zone["max_price"]) < threshold
                ):
                    current_zone["min_price"] = min(
                        current_zone["min_price"], price
                    )
                    current_zone["max_price"] = max(
                        current_zone["max_price"], price
                    )
                    current_zone["hits"] += 1
                    current_zone["indices"].append(idx)
                else:
                    # Si la zona actual tiene suficientes hits, añadirla a las zonas
                    if current_zone["hits"] > 0:
                        zones.append(current_zone)

                    # Iniciar nueva zona
                    current_zone = {
                        "min_price": price,
                        "max_price": price,
                        "hits": 1,
                        "indices": [idx],
                    }

            # Añadir la última zona si tiene hits
            if current_zone["hits"] > 0:
                zones.append(current_zone)

            return zones

        # Identificar zonas de resistencia (altas) y soporte (bajas)
        resistance_zones_short = identify_zones(bf_short, high_prices)
        support_zones_short = identify_zones(bl_short, low_prices)

        resistance_zones_mid = identify_zones(bf_mid, high_prices, window=0.008)
        support_zones_mid = identify_zones(bl_mid, low_prices, window=0.008)

        # 3. Asignar fuerza a cada zona basada en volumen y número de toques
        def calculate_zone_strength(zones, volumes):
            """
            Calcula la fuerza de cada zona basada en volumen y número de toques.
            """
            for zone in zones:
                vol_sum = sum(volumes.iloc[i] for i in zone["indices"])
                zone["strength"] = (zone["hits"] * vol_sum) / len(
                    zone["indices"]
                )

            # Ordenar zonas por fuerza
            return sorted(zones, key=lambda x: x["strength"], reverse=True)

        # Calcular fuerza de zonas
        resistance_zones_short = calculate_zone_strength(
            resistance_zones_short, volumes
        )
        support_zones_short = calculate_zone_strength(
            support_zones_short, volumes
        )

        resistance_zones_mid = calculate_zone_strength(
            resistance_zones_mid, volumes
        )
        support_zones_mid = calculate_zone_strength(support_zones_mid, volumes)

        # --- Analizar reacciones de precio en zonas ---

        # Precios actuales
        current_price = close_prices.iloc[-1]
        current_high = high_prices.iloc[-1]
        current_low = low_prices.iloc[-1]
        current_open = open_prices.iloc[-1]

        # 1. Verificar si el precio está en una zona SR
        in_resistance_zone = False
        in_support_zone = False
        nearest_resistance = None
        nearest_support = None

        # Revisar zonas de resistencia corto plazo
        for zone in resistance_zones_short[:3]:  # Top 3 zonas más fuertes
            if (
                current_high >= zone["min_price"]
                and current_price <= zone["max_price"] * 1.005
            ):
                in_resistance_zone = True
                nearest_resistance = zone
                break

        # Si no encontramos, revisar zonas de resistencia medio plazo
        if not in_resistance_zone:
            for zone in resistance_zones_mid[:2]:  # Top 2 zonas más fuertes
                if (
                    current_high >= zone["min_price"]
                    and current_price <= zone["max_price"] * 1.008
                ):
                    in_resistance_zone = True
                    nearest_resistance = zone
                    break

        # Revisar zonas de soporte corto plazo
        for zone in support_zones_short[:3]:  # Top 3 zonas más fuertes
            if (
                current_low <= zone["max_price"]
                and current_price >= zone["min_price"] * 0.995
            ):
                in_support_zone = True
                nearest_support = zone
                break

        # Si no encontramos, revisar zonas de soporte medio plazo
        if not in_support_zone:
            for zone in support_zones_mid[:2]:  # Top 2 zonas más fuertes
                if (
                    current_low <= zone["max_price"]
                    and current_price >= zone["min_price"] * 0.992
                ):
                    in_support_zone = True
                    nearest_support = zone
                    break

        # 2. Detectar reacción en la zona (price action)
        # Calcular tamaño del cuerpo y sombras
        body_size = abs(current_price - current_open)
        upper_wick = current_high - max(current_open, current_price)
        lower_wick = min(current_open, current_price) - current_low

        # Vela alcista o bajista
        bullish_candle = current_price > current_open
        bearish_candle = current_price < current_open

        # Patrón de rechazo en resistencia
        rejection_at_resistance = (
            in_resistance_zone
            and bearish_candle
            and upper_wick > body_size * 1.5
        )

        # Patrón de rechazo en soporte
        rejection_at_support = (
            in_support_zone and bullish_candle and lower_wick > body_size * 1.5
        )

        # Patrón de ruptura de resistencia
        breakout_resistance = (
            nearest_resistance is not None
            and current_price > nearest_resistance["max_price"] * 1.002
            and bullish_candle
            and body_size
            > (high_prices.iloc[-5:] - low_prices.iloc[-5:]).mean() * 0.5
        )

        # Patrón de ruptura de soporte
        breakdown_support = (
            nearest_support is not None
            and current_price < nearest_support["min_price"] * 0.998
            and bearish_candle
            and body_size
            > (high_prices.iloc[-5:] - low_prices.iloc[-5:]).mean() * 0.5
        )

        # --- Confirmación con indicadores adicionales ---

        # 1. RSI para sobrecompra/sobreventa
        rsi = ta.momentum.RSIIndicator(close=close_prices, window=7).rsi()
        current_rsi = rsi.iloc[-1]

        oversold = current_rsi < 30
        overbought = current_rsi > 70

        # 2. Tendencia direccional con ADX
        adx = ta.trend.ADXIndicator(
            high=high_prices, low=low_prices, close=close_prices, window=14
        )

        di_pos = adx.adx_pos()
        di_neg = adx.adx_neg()
        adx_value = adx.adx()

        strong_trend = adx_value.iloc[-1] > 25
        bullish_trend = di_pos.iloc[-1] > di_neg.iloc[-1]
        bearish_trend = di_pos.iloc[-1] < di_neg.iloc[-1]

        # 3. Análisis de Volumen
        volume_increasing = volumes.iloc[-1] > volumes.iloc[-5:].mean() * 1.3

        # --- Condiciones finales de trading ---

        # Condiciones de compra
        buy_conditions = [
            # Rebote en soporte con confirmación y volumen
            (rejection_at_support and oversold and volume_increasing),
            # Ruptura de resistencia con confirmación de tendencia
            (
                breakout_resistance
                and strong_trend
                and bullish_trend
                and volume_increasing
            ),
            # Doble toque en soporte (acumulación)
            (
                in_support_zone
                and support_zones_short[0]["hits"] >= 2
                and bullish_candle
                and current_rsi > rsi.iloc[-2]
            ),
            # Pullback a zona de soporte en tendencia alcista
            (
                in_support_zone
                and bullish_trend
                and strong_trend
                and current_rsi > 40
                and current_rsi < 60
            ),
        ]

        # Condiciones de venta
        sell_conditions = [
            # Rechazo en resistencia con confirmación y volumen
            (rejection_at_resistance and overbought and volume_increasing),
            # Ruptura de soporte con confirmación de tendencia
            (
                breakdown_support
                and strong_trend
                and bearish_trend
                and volume_increasing
            ),
            # Doble toque en resistencia (distribución)
            (
                in_resistance_zone
                and resistance_zones_short[0]["hits"] >= 2
                and bearish_candle
                and current_rsi < rsi.iloc[-2]
            ),
            # Pullback a zona de resistencia en tendencia bajista
            (
                in_resistance_zone
                and bearish_trend
                and strong_trend
                and current_rsi < 60
                and current_rsi > 40
            ),
        ]

        # Generar señal final
        if any(buy_conditions):
            return self._build_signal(choices.OrderSide.BUY)
        elif any(sell_conditions):
            return self._build_signal(choices.OrderSide.SELL)

        return self._build_signal(choices.OrderSide.HOLD)
