import ta

from apps.trading import choices
from apps.trading.strategies._base import TradingStrategy


class AggregatedOrderFlowStrategy(TradingStrategy):
    """
    Estrategia basada en Order Flow agregado para timeframes de 15 minutos.
    Analiza imbalances de compra/venta, acumulación/distribución y presión compradora.
    Altamente efectiva para anticipar movimientos en mercados líquidos de crypto.
    """

    def generate_signal(self):
        # Parámetros optimizados para 15 minutos
        lookback = 20  # 5 horas de datos

        # --- Indicadores de order flow ---

        # 1. Money Flow Index (MFI) - versión mejorada de RSI con volumen
        high = self.df["high"]
        low = self.df["low"]
        close = self.df["close"]
        volume = self.df["volume"]

        typical_price = (high + low + close) / 3
        raw_money_flow = typical_price * volume

        # Separar flujos positivos y negativos
        positive_flow = raw_money_flow.copy()
        negative_flow = raw_money_flow.copy()

        # Asignar valores según dirección
        for i in range(1, len(typical_price)):
            if typical_price.iloc[i] > typical_price.iloc[i - 1]:
                negative_flow.iloc[i] = 0
            elif typical_price.iloc[i] < typical_price.iloc[i - 1]:
                positive_flow.iloc[i] = 0
            else:
                positive_flow.iloc[i] = 0
                negative_flow.iloc[i] = 0

        # Calcular MFI
        positive_mf = positive_flow.rolling(window=14).sum()
        negative_mf = negative_flow.rolling(window=14).sum()

        mfi = 100 - (100 / (1 + positive_mf / negative_mf))

        # 2. Accumulation/Distribution Line
        ad_line = ta.volume.AccumulationDistributionIndex(
            high=high, low=low, close=close, volume=volume
        ).acc_dist_index()

        # Suavizar AD Line para reducir ruido
        ad_ema = ad_line.ewm(span=5).mean()

        # 3. On-Balance Volume con análisis de divergencia
        obv = ta.volume.OnBalanceVolumeIndicator(
            close, volume
        ).on_balance_volume()
        obv_ema = obv.ewm(span=8).mean()

        # 4. Volumen Delta (estimación de presión compradora vs vendedora)
        # En ausencia de datos tick, estimamos con high-low-close
        buy_pressure = ((close - low) / (high - low + 0.000001)) * volume
        sell_pressure = ((high - close) / (high - low + 0.000001)) * volume

        delta_volume = buy_pressure - sell_pressure
        cumulative_delta = delta_volume.rolling(window=lookback).sum()

        # 5. Volume Weighted Average Price (VWAP) como referencia
        vwap = (typical_price * volume).cumsum() / volume.cumsum()

        # 6. Volume Weighted MACD para filtrar señales falsas
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26

        # Ponderamos MACD por volumen
        vol_macd = macd_line * (volume / volume.rolling(window=20).mean())
        vol_macd_signal = vol_macd.ewm(span=9, adjust=False).mean()

        # --- Análisis de Order Flow ---

        # Analizar últimas velas para condiciones actuales
        current_close = close.iloc[-1]
        current_mfi = mfi.iloc[-1]
        current_obv = obv.iloc[-1]
        current_obv_ema = obv_ema.iloc[-1]
        current_delta = cumulative_delta.iloc[-1]
        current_vwap = vwap.iloc[-1]

        # Detectar divergencias y acumulación/distribución
        price_higher = close.iloc[-1] > close.iloc[-lookback]
        obv_higher = obv.iloc[-1] > obv.iloc[-lookback]
        ad_higher = ad_line.iloc[-1] > ad_line.iloc[-lookback]

        # Divergencia alcista: OBV/AD Line sube pero precio no
        bullish_divergence = not price_higher and (obv_higher or ad_higher)

        # Divergencia bajista: OBV/AD Line baja pero precio no
        bearish_divergence = price_higher and (not obv_higher and not ad_higher)

        # Balance comprador/vendedor actual
        buying_pressure = current_delta > 0
        strong_buying = (
            current_delta > cumulative_delta.iloc[-lookback:].std() * 1.5
        )
        strong_selling = (
            current_delta < -cumulative_delta.iloc[-lookback:].std() * 1.5
        )

        # Análisis de MFI para sobrecompra/sobreventa con momentum
        overbought = current_mfi > 80
        oversold = current_mfi < 20
        mfi_rising = mfi.iloc[-1] > mfi.iloc[-2] > mfi.iloc[-3]
        mfi_falling = mfi.iloc[-1] < mfi.iloc[-2] < mfi.iloc[-3]

        # Relación con VWAP para timing de entrada
        above_vwap = current_close > current_vwap
        below_vwap = current_close < current_vwap

        # Análisis de Volume-Weighted MACD para señales
        vm_crossover_bull = (
            vol_macd.iloc[-2] < vol_macd_signal.iloc[-2]
            and vol_macd.iloc[-1] > vol_macd_signal.iloc[-1]
        )

        vm_crossover_bear = (
            vol_macd.iloc[-2] > vol_macd_signal.iloc[-2]
            and vol_macd.iloc[-1] < vol_macd_signal.iloc[-1]
        )

        # Análisis de expansión de volumen (importante para 15 min)
        avg_volume = volume.rolling(window=20).mean()
        volume_expanding = volume.iloc[-3:].mean() > avg_volume.iloc[-1] * 1.2

        # --- Generación de señales basadas en Order Flow ---

        # Señales de compra
        buy_signals = [
            # Acumulación con presión compradora
            (buying_pressure and ad_higher and obv_higher and above_vwap),
            # Rebote en sobreventa con señal de MACD
            (oversold and mfi_rising and vm_crossover_bull),
            # Fuerte presión compradora sobre VWAP
            (strong_buying and above_vwap and volume_expanding),
            # Divergencia alcista con confirmación de volumen
            (
                bullish_divergence
                and current_obv > current_obv_ema
                and volume_expanding
            ),
            # Impulso alcista con confirmación de MFI
            (vm_crossover_bull and current_mfi > 50 and buying_pressure),
        ]

        # Señales de venta
        sell_signals = [
            # Distribución con presión vendedora
            (
                not buying_pressure
                and not ad_higher
                and not obv_higher
                and below_vwap
            ),
            # Rechazo en sobrecompra con señal de MACD
            (overbought and mfi_falling and vm_crossover_bear),
            # Fuerte presión vendedora bajo VWAP
            (strong_selling and below_vwap and volume_expanding),
            # Divergencia bajista con confirmación de volumen
            (
                bearish_divergence
                and current_obv < current_obv_ema
                and volume_expanding
            ),
            # Impulso bajista con confirmación de MFI
            (vm_crossover_bear and current_mfi < 50 and not buying_pressure),
        ]

        # Generar señales finales
        if any(buy_signals):
            return self._build_signal(choices.OrderSide.BUY)
        elif any(sell_signals):
            return self._build_signal(choices.OrderSide.SELL)

        return self._build_signal(choices.OrderSide.HOLD)
