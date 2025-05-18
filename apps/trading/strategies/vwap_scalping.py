import pandas as pd
import ta

from apps.trading import choices
from apps.trading.strategies._base import TradingStrategy


class VWAPScalpingStrategy(TradingStrategy):
    """
    Estrategia de scalping basada en VWAP para timeframes de 15 minutos.
    Aprovecha desviaciones del VWAP y su comportamiento como soporte/resistencia.
    Ideal para mercados de alta liquidez y volatilidad moderada.
    """

    def generate_signal(self):
        # Datos de entrada
        open_prices = self.df["open"]
        high_prices = self.df["high"]
        low_prices = self.df["low"]
        close_prices = self.df["close"]
        volumes = self.df["volume"]

        # --- Cálculo de VWAP y bandas ---

        # 1. VWAP estándar (Volume Weighted Average Price)
        typical_price = (high_prices + low_prices + close_prices) / 3
        vwap_raw = (typical_price * volumes).cumsum() / volumes.cumsum()

        # Para mejor adaptación a 15 minutos, calcular VWAP por sesiones
        # Simulamos sesión de 8 horas (32 velas de 15 min)
        session_size = 32

        # Inicializar VWAP por sesiones
        vwap = pd.Series(index=close_prices.index)

        for i in range(0, len(close_prices), session_size):
            end_idx = min(i + session_size, len(close_prices))
            session_slice = slice(i, end_idx)

            session_tp = typical_price.iloc[session_slice]
            session_vol = volumes.iloc[session_slice]

            session_vwap = (
                session_tp * session_vol
            ).cumsum() / session_vol.cumsum()
            vwap.iloc[session_slice] = session_vwap.values

        # Rellenar NaN con valores forward-fill
        vwap = vwap.fillna(method="ffill")

        # 2. Bandas de desviación alrededor del VWAP
        # Usar ATR para bandas adaptativas
        atr = ta.volatility.AverageTrueRange(
            high=high_prices, low=low_prices, close=close_prices, window=14
        ).average_true_range()

        # Crear bandas a diferentes desviaciones
        vwap_upper1 = vwap + 1.0 * atr
        vwap_lower1 = vwap - 1.0 * atr

        vwap_upper2 = vwap + 2.0 * atr
        vwap_lower2 = vwap - 2.0 * atr

        vwap_upper3 = vwap + 3.0 * atr
        vwap_lower3 = vwap - 3.0 * atr

        # 3. Métricas de desviación de VWAP
        # Distancia porcentual al VWAP
        vwap_distance = (close_prices - vwap) / vwap * 100

        # Pendiente de VWAP (dirección del VWAP)
        vwap_slope = (vwap - vwap.shift(4)) / vwap.shift(4) * 100

        # --- Indicadores complementarios ---

        # 1. Oscilador VWAP (deviación normalizada del precio respecto al VWAP)
        # Para medir momentum relativo al VWAP
        vwap_oscillator = (close_prices - vwap) / atr

        # 2. Volumen relativo
        avg_volume = volumes.rolling(window=20).mean()
        rel_volume = volumes / avg_volume

        # 3. Stochastic RSI para timing
        rsi = ta.momentum.RSIIndicator(close_prices, window=14).rsi()
        stoch_k = (
            100
            * (rsi - rsi.rolling(window=14).min())
            / (rsi.rolling(window=14).max() - rsi.rolling(window=14).min())
        )
        stoch_d = stoch_k.rolling(window=3).mean()

        # --- Análisis técnico para filtros ---

        # 1. EMAs cortas para tendencia inmediata
        ema8 = close_prices.ewm(span=8).mean()
        ema21 = close_prices.ewm(span=21).mean()

        # Tendencia de corto plazo
        uptrend_short = ema8 > ema21
        downtrend_short = ema8 < ema21

        # 2. Chaikin Money Flow (CMF) para confirmar dirección
        high_low_range = high_prices - low_prices
        money_flow_multiplier = (
            (close_prices - low_prices) - (high_prices - close_prices)
        ) / high_low_range
        money_flow_volume = money_flow_multiplier * volumes
        cmf = (
            money_flow_volume.rolling(window=20).sum()
            / volumes.rolling(window=20).sum()
        )

        # --- Condiciones de entrada ---

        # Datos actuales
        current_price = close_prices.iloc[-1]
        current_vwap = vwap.iloc[-1]
        current_vwap_dist = vwap_distance.iloc[-1]
        current_vwap_slope = vwap_slope.iloc[-1]
        current_vwap_osc = vwap_oscillator.iloc[-1]
        current_volume = rel_volume.iloc[-1]
        current_cmf = cmf.iloc[-1]

        # Previous values
        prev_price = close_prices.iloc[-2]
        prev_vwap_dist = vwap_distance.iloc[-2]

        # Patrón de vela
        bullish_candle = current_price > open_prices.iloc[-1]
        bearish_candle = current_price < open_prices.iloc[-1]

        # --- Patrones de VWAP Scalping ---

        # 1. Regresión a la media básica (Mean Reversion)
        mr_buy_signal = (
            current_vwap_dist
            < -1.5  # Precio significativamente por debajo del VWAP
            and current_vwap_osc < -1.0  # Confirmación con oscilador
            and current_vwap_dist
            > prev_vwap_dist  # Comenzando a revertir hacia el VWAP
            and current_price > prev_price  # Momentum de precio subiendo
            and current_volume > 1.2  # Volumen por encima del promedio
        )

        mr_sell_signal = (
            current_vwap_dist
            > 1.5  # Precio significativamente por encima del VWAP
            and current_vwap_osc > 1.0  # Confirmación con oscilador
            and current_vwap_dist
            < prev_vwap_dist  # Comenzando a revertir hacia el VWAP
            and current_price < prev_price  # Momentum de precio bajando
            and current_volume > 1.2  # Volumen por encima del promedio
        )

        # 2. VWAP como soporte/resistencia
        vwap_support_bounce = (
            abs(low_prices.iloc[-1] - current_vwap) / current_vwap
            < 0.002  # Tocó el VWAP
            and bullish_candle  # Rebotó hacia arriba
            and current_vwap_slope > 0  # VWAP en tendencia alcista
            and current_cmf > 0  # Confirmación de flujo de dinero
        )

        vwap_resistance_rejection = (
            abs(high_prices.iloc[-1] - current_vwap) / current_vwap
            < 0.002  # Tocó el VWAP
            and bearish_candle  # Rebotó hacia abajo
            and current_vwap_slope < 0  # VWAP en tendencia bajista
            and current_cmf < 0  # Confirmación de flujo de dinero
        )

        # 3. Cruce de bandas VWAP
        vwap_band_crossover_buy = (
            close_prices.iloc[-2]
            < vwap_lower2.iloc[-2]  # Precio estaba por debajo de banda inferior
            and current_price > vwap_lower2.iloc[-1]  # Cruzó hacia arriba
            and current_vwap_slope > -0.2  # VWAP relativamente plano o subiendo
            and stoch_k.iloc[-1]
            > stoch_d.iloc[-1]  # Confirmación con estocástico
            and stoch_k.iloc[-1] > 20  # No demasiado sobrevendido
        )

        vwap_band_crossover_sell = (
            close_prices.iloc[-2]
            > vwap_upper2.iloc[-2]  # Precio estaba por encima de banda superior
            and current_price < vwap_upper2.iloc[-1]  # Cruzó hacia abajo
            and current_vwap_slope < 0.2  # VWAP relativamente plano o bajando
            and stoch_k.iloc[-1]
            < stoch_d.iloc[-1]  # Confirmación con estocástico
            and stoch_k.iloc[-1] < 80  # No demasiado sobrecomprado
        )

        # 4. Divergencia extrema y retorno (sólo con alto volumen)
        extreme_deviation_buy = (
            current_vwap_dist < -3.0  # Deviación extrema hacia abajo
            and current_vwap_osc < -2.5  # Oscilador confirma extremo
            and current_price > prev_price  # Comenzando a revertir
            and current_volume > 2.0  # Volumen muy alto
            and stoch_k.iloc[-1] < 20
            and stoch_k.iloc[-1]
            > stoch_k.iloc[-2]  # Estocástico en sobreventa y subiendo
        )

        extreme_deviation_sell = (
            current_vwap_dist > 3.0  # Deviación extrema hacia arriba
            and current_vwap_osc > 2.5  # Oscilador confirma extremo
            and current_price < prev_price  # Comenzando a revertir
            and current_volume > 2.0  # Volumen muy alto
            and stoch_k.iloc[-1] > 80
            and stoch_k.iloc[-1]
            < stoch_k.iloc[-2]  # Estocástico en sobrecompra y bajando
        )

        # --- Condiciones finales agrupadas ---

        # Señales de compra
        buy_signals = [
            mr_buy_signal,
            vwap_support_bounce,
            vwap_band_crossover_buy,
            extreme_deviation_buy,
        ]

        # Señales de venta
        sell_signals = [
            mr_sell_signal,
            vwap_resistance_rejection,
            vwap_band_crossover_sell,
            extreme_deviation_sell,
        ]

        # Filtro adicional de tendencia para mejorar aciertos
        trend_filter_buy = uptrend_short.iloc[-1] or current_vwap_slope > 0.5
        trend_filter_sell = (
            downtrend_short.iloc[-1] or current_vwap_slope < -0.5
        )

        # Generar señal final
        if any(buy_signals) and trend_filter_buy:
            return self._build_signal(choices.OrderSide.BUY)
        elif any(sell_signals) and trend_filter_sell:
            return self._build_signal(choices.OrderSide.SELL)

        return self._build_signal(choices.OrderSide.HOLD)
