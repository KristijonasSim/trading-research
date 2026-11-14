"""
Estrategia baseline educativa: EMA Cross + RSI Filter (Fase 1 - Sin ML).

Objetivo del archivo
-------------------
Servir como estrategia de referencia para:
1) aprender arquitectura de Freqtrade,
2) validar pipeline de datos/backtest,
3) comparar contra estrategias con ML.

Resumen de logica
-----------------
- Entrada: cruce alcista EMA rapida/EMA lenta + filtro RSI + filtro volumen.
- Filtro de regimen: operar solo con cierre sobre EMA200.
- Filtro de volatilidad: evitar condiciones extremas (ATR/close alto).
- Salida: cruce bajista o RSI extremo.
- Riesgo: stoploss fijo + trailing + ROI escalonado.

Importante
----------
- Es una baseline, no una estrategia lista para live.
- Antes de considerar dinero real: validation/final-test, dry-run y control de DD.
- Hyperopt sin validacion temporal robusta tiende a sobreoptimizacion.
"""

from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from pandas import DataFrame
import talib.abstract as ta


class EmaCrossRsi(IStrategy):
    """
    Baseline simple basada en cruce de EMAs con filtro RSI.

    Esta clase implementa los tres hooks principales de Freqtrade:
    - populate_indicators(): calcula columnas tecnicas.
    - populate_entry_trend(): marca entradas long con enter_long=1.
    - populate_exit_trend(): marca salidas long con exit_long=1.

    Convencion de trazabilidad:
    - enter_tag y exit_tag se llenan para auditar motivos de entrada/salida.
    """

    # Versión de la estrategia (incrementar al hacer cambios)
    INTERFACE_VERSION = 3

    # Timeframe de las velas
    timeframe = "1h"

    # Stoploss: -5% desde el precio de entrada
    stoploss = -0.05

    # Trailing stop: protege ganancias cuando el precio sube
    trailing_stop = True
    trailing_stop_positive = 0.01       # Activa trailing cuando tiene +1%
    trailing_stop_positive_offset = 0.02 # Solo activa si alcanza +2%
    trailing_only_offset_is_reached = True

    # ROI (Return on Investment) — toma de ganancias escalonada
    # "0": vende si tiene +8% en cualquier momento
    # "60": después de 60 minutos, vende si tiene +4%
    # "120": después de 120 minutos, vende si tiene +2%
    minimal_roi = {
        "0": 0.08,
        "60": 0.04,
        "120": 0.02,
    }

    # Solo comprar al inicio de una nueva vela (no a mitad de vela)
    process_only_new_candles = True

    # No usar señales de salida del order book
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # Número de velas necesarias para calcular indicadores
    startup_candle_count: int = 220

    @property
    def protections(self):
        """
        Protecciones de riesgo usadas en backtest, dry-run y live.

        Freqtrade estable actual recomienda definir protecciones en estrategia
        y activarlas en backtesting con `--enable-protections`.
        """
        return [
            {
                "method": "CooldownPeriod",
                "stop_duration_candles": 2,
            },
            {
                "method": "StoplossGuard",
                "trade_limit": 3,
                "lookback_period_candles": 24,
                "stop_duration_candles": 12,
                "required_profit": 0.0,
                "only_per_pair": False,
            },
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 72,
                "trade_limit": 20,
                "stop_duration_candles": 48,
                "max_allowed_drawdown": 0.12,
            },
            {
                "method": "LowProfitPairs",
                "lookback_period_candles": 96,
                "trade_limit": 4,
                "stop_duration_candles": 48,
                "required_profit": 0.0,
            },
        ]

    # --- Parámetros optimizables (para Hyperopt en el futuro) ---
    ema_fast_period = IntParameter(10, 30, default=20, space="buy", optimize=True)
    ema_slow_period = IntParameter(40, 70, default=50, space="buy", optimize=True)
    rsi_period = IntParameter(10, 20, default=14, space="buy", optimize=True)
    rsi_buy_limit = IntParameter(20, 70, default=70, space="buy", optimize=True)
    rsi_sell_limit = IntParameter(70, 90, default=80, space="sell", optimize=True)
    max_volatility = DecimalParameter(0.01, 0.06, default=0.03, space="buy", optimize=False)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Calcula indicadores requeridos por la estrategia.

        Args:
            dataframe: OHLCV historico del par/timeframe actual.
            metadata: Informacion del par (ej. {'pair': 'BTC/USDT'}).

        Returns:
            DataFrame con columnas agregadas:
            - ema_fast, ema_slow
            - rsi
            - ema_regime
            - atr, volatility_ratio
            - volume_mean_20

        Notas:
        - startup_candle_count=220 asegura datos suficientes para EMA200.
        - volatility_ratio = ATR/close se usa como guardrail de riesgo.
        """
        # EMAs (Exponential Moving Averages)
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=self.ema_fast_period.value)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=self.ema_slow_period.value)

        # RSI (Relative Strength Index) — mide sobrecompra/sobreventa
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=self.rsi_period.value)

        # Regimen de mercado (filtro): operar solo arriba de EMA200
        dataframe["ema_regime"] = ta.EMA(dataframe, timeperiod=200)

        # Volatilidad relativa para evitar condiciones extremas
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["volatility_ratio"] = dataframe["atr"] / dataframe["close"]

        # Volumen promedio de 20 periodos (para filtrar pares con poco volumen)
        dataframe["volume_mean_20"] = dataframe["volume"].rolling(window=20).mean()

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Define condiciones de entrada long.

        Args:
            dataframe: DataFrame con indicadores ya calculados.
            metadata: Metadata de Freqtrade (no requerida por la logica).

        Returns:
            DataFrame con:
            - enter_long=1 cuando se cumplen todas las condiciones.
            - enter_tag='ema_cross_rsi_regime' para auditoria.

        Condiciones de entrada:
        1) Cruce alcista EMA fast sobre EMA slow.
        2) RSI por debajo del limite de compra.
        3) Volumen actual mayor al umbral relativo.
        4) Cierre por encima de EMA200 (regimen alcista).
        5) Volatilidad por debajo de max_volatility.
        """
        dataframe.loc[
            (
                # Condición 1: EMA rápida cruza por encima de EMA lenta
                (dataframe["ema_fast"] > dataframe["ema_slow"])
                & (dataframe["ema_fast"].shift(1) <= dataframe["ema_slow"].shift(1))
                # Condición 2: RSI no está en sobrecompra (filtro de seguridad)
                & (dataframe["rsi"] < self.rsi_buy_limit.value)
                # Condición 3: Hay volumen (evita señales en mercado muerto)
                & (dataframe["volume"] > dataframe["volume_mean_20"] * 0.5)
                # Condición 4: Volumen no es cero
                & (dataframe["volume"] > 0)
                # Condicion 5: Regimen favorable (close por encima de EMA200)
                & (dataframe["close"] > dataframe["ema_regime"])
                # Condicion 6: Evitar volatilidad extrema
                & (dataframe["volatility_ratio"] < self.max_volatility.value)
            ),
            ["enter_long", "enter_tag"],
        ] = 1

        dataframe.loc[
            dataframe["enter_long"] == 1,
            "enter_tag",
        ] = "ema_cross_rsi_regime"

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Define condiciones de salida long.

        Args:
            dataframe: DataFrame con indicadores ya calculados.
            metadata: Metadata de Freqtrade (no requerida por la logica).

        Returns:
            DataFrame con:
            - exit_long=1 cuando hay senal de salida.
            - exit_tag='ema_cross_or_rsi_extreme' para auditoria.

        Nota:
            Stoploss, trailing y ROI pueden cerrar trades aunque exit_long no sea 1.
        """
        dataframe.loc[
            (
                # Condición 1: EMA rápida cruza por debajo de EMA lenta (tendencia bajista)
                (
                    (dataframe["ema_fast"] < dataframe["ema_slow"])
                    & (dataframe["ema_fast"].shift(1) >= dataframe["ema_slow"].shift(1))
                )
                # O Condición 2: RSI en sobrecompra extrema
                | (dataframe["rsi"] > self.rsi_sell_limit.value)
            ),
            ["exit_long", "exit_tag"],
        ] = 1

        dataframe.loc[
            dataframe["exit_long"] == 1,
            "exit_tag",
        ] = "ema_cross_or_rsi_extreme"

        return dataframe
