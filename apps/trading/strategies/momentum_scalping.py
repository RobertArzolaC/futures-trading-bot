import ta

from apps.trading import choices
from apps.trading.strategies._base import TradingStrategy


class MomentumScalpingStrategy(TradingStrategy):
    """
    Estrategia de Momentum Scalping optimizada para timeframes de 15 minutos.
    Combina análisis de volumen, aceleración de precio y momentum para entradas precisas.
    Ideal para capturar movimientos rápidos intradía en mercados cripto.
    """

    def generate_signal(self):
        # Configuración específica para 15 minutos
        rsi_period = 9  # RSI más corto para mayor sensibilidad
        volume_lookback = 12  # 3 horas de datos

        # Calcular RSI
        rsi = ta.momentum.RSIIndicator(
            self.df["close"], window=rsi_period
        ).rsi()

        # Calcular cambio de precio (aceleración)
        self.df["price_change"] = self.df["close"].pct_change(periods=3)

        # Calcular media móvil exponencial corta para la tendencia inmediata
        ema5 = self.df["close"].ewm(span=5).mean()
        ema13 = self.df["close"].ewm(span=13).mean()

        # Análisis de volumen
        avg_volume = self.df["volume"].rolling(window=volume_lookback).mean()
        volume_surge = self.df["volume"] > (
            avg_volume * 1.4
        )  # 40% sobre promedio

        # Combinación de indicadores para momentum
        # Calcular pendiente de RSI (aceleración de momentum)
        rsi_slope = rsi - rsi.shift(2)

        # Condiciones actuales
        current_price = self.df["close"].iloc[-1]
        prev_price = self.df["close"].iloc[-2]
        current_rsi = rsi.iloc[-1]
        current_rsi_slope = rsi_slope.iloc[-1]

        # Señales de compra
        buy_conditions = (
            (current_rsi < 60)  # No sobrecomprado
            & (current_rsi > 40)  # No sobreventa
            & (current_rsi_slope > 2)  # RSI acelerando hacia arriba
            & (ema5.iloc[-1] > ema13.iloc[-1])  # Tendencia alcista corto plazo
            & (volume_surge.iloc[-1])  # Confirmación de volumen
        )

        # Señales potentes de compra con momentum adicional
        strong_buy_conditions = (
            (
                self.df["price_change"].iloc[-1] > 0.005
            )  # Movimiento alcista > 0.5%
            & (current_rsi > 45)  # Momento positivo
            & (current_rsi < 65)  # No extremadamente sobrecomprado
            & (current_rsi_slope > 4)  # Aceleración rápida
            & (volume_surge.iloc[-1])  # Alto volumen
            & (ema5.iloc[-2] <= ema13.iloc[-2])  # Cruce reciente
            & (ema5.iloc[-1] > ema13.iloc[-1])  # Cruce confirmado
        )

        # Señales de venta
        sell_conditions = (
            (current_rsi > 40)  # No sobreventa
            & (current_rsi < 60)  # No sobrecomprado
            & (current_rsi_slope < -2)  # RSI acelerando hacia abajo
            & (ema5.iloc[-1] < ema13.iloc[-1])  # Tendencia bajista corto plazo
            & (volume_surge.iloc[-1])  # Confirmación de volumen
        )

        # Señales potentes de venta con momentum adicional
        strong_sell_conditions = (
            (
                self.df["price_change"].iloc[-1] < -0.005
            )  # Movimiento bajista > 0.5%
            & (current_rsi < 55)  # Momento negativo
            & (current_rsi > 35)  # No extremadamente sobrevendido
            & (current_rsi_slope < -4)  # Aceleración rápida abajo
            & (volume_surge.iloc[-1])  # Alto volumen
            & (ema5.iloc[-2] >= ema13.iloc[-2])  # Cruce reciente
            & (ema5.iloc[-1] < ema13.iloc[-1])  # Cruce confirmado
        )

        # Detección de divergencias (más fiables para 15 min)
        price_higher_high = current_price > self.df["close"].iloc[-3:-1].max()
        price_lower_low = current_price < self.df["close"].iloc[-3:-1].min()

        rsi_higher_high = current_rsi > rsi.iloc[-3:-1].max()
        rsi_lower_low = current_rsi < rsi.iloc[-3:-1].min()

        # Divergencia bajista: precio hace máximos más altos pero RSI no
        bearish_divergence = price_higher_high and not rsi_higher_high

        # Divergencia alcista: precio hace mínimos más bajos pero RSI no
        bullish_divergence = price_lower_low and not rsi_lower_low

        # Señales intradía basadas en todo el análisis
        if strong_buy_conditions or (buy_conditions and bullish_divergence):
            return self._build_signal(choices.OrderSide.BUY)
        elif strong_sell_conditions or (sell_conditions and bearish_divergence):
            return self._build_signal(choices.OrderSide.SELL)

        return self._build_signal(choices.OrderSide.HOLD)
