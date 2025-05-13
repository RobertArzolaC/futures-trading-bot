import ta

from apps.trading import choices
from apps.trading.strategies._base import TradingStrategy


class CryptoSeasonalityMomentumStrategy(TradingStrategy):
    """
    Estrategia que combina patrones estacionales de crypto con momentum.
    Aprovecha los ciclos conocidos del mercado crypto (halving, alt season, etc.)
    y los combina con indicadores de momentum para timing preciso.
    """

    def generate_signal(self):
        # Indicadores de momentum
        rsi = ta.momentum.RSIIndicator(self.df["close"], window=14).rsi()

        # MACD para momentum
        macd = ta.trend.MACD(self.df["close"])
        macd_line = macd.macd()
        signal_line = macd.macd_signal()

        # Money Flow Index (MFI) - RSI con volumen
        high = self.df["high"]
        low = self.df["low"]
        close = self.df["close"]
        volume = self.df["volume"]
        typical_price = (high + low + close) / 3
        raw_money_flow = typical_price * volume

        positive_flow = raw_money_flow.where(
            typical_price > typical_price.shift(1), 0
        )
        negative_flow = raw_money_flow.where(
            typical_price < typical_price.shift(1), 0
        )

        positive_mf = positive_flow.rolling(14).sum()
        negative_mf = negative_flow.rolling(14).sum()

        mfi = 100 - (100 / (1 + positive_mf / negative_mf))

        # Análisis de dominancia (útil para alt season)
        # Simulamos con volumen relativo y cambio de precio
        btc_correlation = self.df["close"].rolling(30).corr(self.df["volume"])

        # Detectar acumulación (antes de rallies estacionales)
        obv = ta.volume.OnBalanceVolumeIndicator(
            close, volume
        ).on_balance_volume()
        obv_ema = obv.ewm(span=21).mean()
        accumulation = obv > obv_ema

        # Análisis de volatilidad (típicamente baja antes de grandes movimientos)
        bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
        bb_width = bb.bollinger_hband() - bb.bollinger_lband()
        bb_squeeze = bb_width < bb_width.rolling(50).mean() * 0.7

        # Condiciones actuales
        current_price = close.iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_mfi = mfi.iloc[-1]
        current_macd = macd_line.iloc[-1]
        current_signal = signal_line.iloc[-1]

        # Patrones estacionales conocidos en crypto
        # 1. "Enero Effect" - Rally típico de inicio de año
        # 2. "Sell in May" - Debilidad en mayo-junio
        # 3. "Uptober" - Octubre históricamente alcista
        # 4. Rally de fin de año - Noviembre-Diciembre

        # Para simular fecha actual (ya que no tenemos acceso a datetime en el contexto)
        # Usaríamos el índice del dataframe como proxy temporal
        period_in_year = (len(self.df) % 365) / 365  # Aproximación

        # Definir ventanas estacionales favorables
        january_window = period_in_year < 0.1  # Primeros 10% del año
        october_window = 0.75 < period_in_year < 0.85  # Octubre aproximado
        year_end_window = period_in_year > 0.85  # Últimos 15% del año

        # Definir ventanas estacionales desfavorables
        may_june_window = 0.35 < period_in_year < 0.5  # Mayo-Junio aproximado

        # Señales de compra

        # 1. Entrada estacional con confirmación técnica
        if january_window or october_window or year_end_window:
            # Confirmación de momentum positivo
            if (
                current_rsi > 50
                and current_rsi < 70
                and current_macd > current_signal
                and current_mfi > 50
                and accumulation.iloc[-1]
            ):
                return self._build_signal(choices.OrderSide.BUY)

        # 2. Salida de squeeze en período favorable
        if (
            bb_squeeze.iloc[-2] and not bb_squeeze.iloc[-1]
        ):  # Salida del squeeze
            if (
                current_rsi > 45 and current_mfi > 45 and not may_june_window
            ):  # Evitar período débil
                # Confirmar dirección con MACD
                if current_macd > current_signal:
                    return self._build_signal(choices.OrderSide.BUY)

        # 3. Reversión en sobreventa durante período alcista
        if october_window or year_end_window:
            if (
                current_rsi < 35
                and current_mfi < 30
                and obv.iloc[-1] > obv.iloc[-5]
            ):  # OBV aún positivo
                return self._build_signal(choices.OrderSide.BUY)

        # 4. Momentum fuerte con estacionalidad favorable
        macd_momentum = current_macd - current_signal
        if january_window or october_window:
            if (
                macd_momentum > 0
                and macd_momentum
                > (current_macd * 0.1)  # MACD divergiendo fuerte
                and current_mfi > 60
                and btc_correlation.iloc[-1] < 0.5
            ):  # Baja correlación (posible alt season)
                return self._build_signal(choices.OrderSide.BUY)

        # Señales de venta

        # 1. Entrada a período estacional débil
        if may_june_window:
            if current_rsi > 65 or current_mfi > 70:
                return self._build_signal(choices.OrderSide.SELL)

        # 2. Sobrecompra en cualquier período
        if (
            current_rsi > 75
            and current_mfi > 80
            and current_macd < current_signal
        ):
            return self._build_signal(choices.OrderSide.SELL)

        # 3. Pérdida de momentum en período no favorable
        if not (january_window or october_window or year_end_window):
            if (
                current_macd < current_signal
                and macd_line.iloc[-2] > signal_line.iloc[-2]  # Cruce bajista
                and current_mfi < 50
            ):
                return self._build_signal(choices.OrderSide.SELL)

        # 4. Distribución detectada (OBV divergente)
        if (
            current_price > self.df["close"].iloc[-10]
            and obv.iloc[-1] < obv.iloc[-10]
            and current_rsi > 60
        ):
            return self._build_signal(choices.OrderSide.SELL)

        # 5. Alta volatilidad + período débil
        current_bb_width = bb_width.iloc[-1]
        avg_bb_width = bb_width.rolling(50).mean().iloc[-1]

        if (
            current_bb_width > avg_bb_width * 1.5  # Alta volatilidad
            and may_june_window
            and current_rsi > 55
        ):
            return self._build_signal(choices.OrderSide.SELL)

        return self._build_signal(choices.OrderSide.HOLD)
