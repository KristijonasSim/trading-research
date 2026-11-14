"""
Estrategia FreqAI con LightGBMClassifier (Fase 3 - Con ML).

Objetivo del archivo
-------------------
Integrar FreqAI siguiendo el patron oficial para clasificadores:
- Features empiezan con "%".
- Target/clase empieza con "&s-".
- `self.freqai.class_names` define las clases discretas del clasificador.
- La prediccion vuelve en la misma columna target (`&s-up_or_down`).
- `do_predict == 1` indica que FreqAI considera confiable la prediccion.

Principio de riesgo
-------------------
ML no decide solo. Primero debe existir un setup tecnico razonable
(EMA/RSI/regimen); luego FreqAI confirma si la prediccion es "up".
"""

import logging

import numpy as np
from pandas import DataFrame
import talib.abstract as ta

from freqtrade.strategy import IStrategy


logger = logging.getLogger(__name__)


class FreqaiLightgbm(IStrategy):
    """
    Estrategia long-only con confirmacion ML mediante FreqAI.

    Flujo operativo:
    1) Crear features tecnicas para FreqAI.
    2) Crear target clasificador `&s-up_or_down` con clases `down` y `up`.
    3) Ejecutar `self.freqai.start(...)` dentro de `populate_indicators`.
    4) Entrar solo si setup tecnico + `do_predict == 1` + clase predicha `up`.
    5) Salir por senal tecnica o clase predicha `down`.
    """

    INTERFACE_VERSION = 3

    timeframe = "1h"
    stoploss = -0.07

    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True

    minimal_roi = {
        "0": 0.10,
        "120": 0.05,
        "240": 0.02,
    }

    process_only_new_candles = True
    use_exit_signal = True
    startup_candle_count: int = 220

    @property
    def protections(self):
        """
        Protecciones de riesgo usadas en backtest, dry-run y live.

        Mantener las mismas protecciones que la baseline permite comparar
        FreqAI contra EmaCrossRsi bajo un regimen de riesgo equivalente.
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

    def feature_engineering_expand_all(
        self, dataframe: DataFrame, period: int, metadata: dict, **kwargs
    ) -> DataFrame:
        """
        Genera features que FreqAI expandira por periodo/timeframe/par/shift.

        Args:
            dataframe: Velas OHLCV del par actual.
            period: Periodo inyectado por FreqAI desde `indicator_periods_candles`.
            metadata: Metadata del par.

        Returns:
            DataFrame con features `%` reconocidas por FreqAI.

        Nota:
            Todo lo definido aqui puede multiplicarse mucho por la configuracion
            FreqAI. Mantener este set pequeno reduce ruido y overfitting.
        """
        dataframe["%-rsi-period"] = ta.RSI(dataframe, timeperiod=period)
        dataframe["%-pct-change-period"] = dataframe["close"].pct_change(periods=period)
        dataframe["%-close-ema-ratio-period"] = dataframe["close"] / ta.EMA(dataframe, timeperiod=period)
        dataframe["%-volatility-period"] = dataframe["close"].pct_change().rolling(period).std()
        dataframe["%-volume-ratio-period"] = dataframe["volume"] / dataframe["volume"].rolling(period).mean()
        dataframe["%-candle-range-period"] = (
            (dataframe["high"] - dataframe["low"]) / dataframe["close"]
        ).rolling(period).mean()
        return dataframe

    def feature_engineering_expand_basic(
        self, dataframe: DataFrame, metadata: dict, **kwargs
    ) -> DataFrame:
        """
        Genera features que FreqAI expande por timeframe/par/shift, pero no por periodo.

        Args:
            dataframe: Velas OHLCV del par actual.
            metadata: Metadata del par.

        Returns:
            DataFrame con features `%` basicas.
        """
        dataframe["%-raw-return"] = dataframe["close"].pct_change()
        dataframe["%-is-green"] = (dataframe["close"] > dataframe["open"]).astype(int)
        dataframe["%-volume-change"] = dataframe["volume"].pct_change()
        return dataframe

    def feature_engineering_standard(
        self, dataframe: DataFrame, metadata: dict, **kwargs
    ) -> DataFrame:
        """
        Genera features de base timeframe que NO deben autoexpandirse.

        Args:
            dataframe: Velas OHLCV del timeframe base.
            metadata: Metadata del par.

        Returns:
            DataFrame con features temporales normalizadas.

        Uso:
            Hora y dia de semana se ubican aqui porque no tiene sentido
            duplicarlas por cada periodo de indicador.
        """
        dataframe["%-day_of_week"] = (dataframe["date"].dt.dayofweek + 1) / 7
        dataframe["%-hour_of_day"] = (dataframe["date"].dt.hour + 1) / 25
        return dataframe

    def set_freqai_targets(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        """
        Define target clasificador oficial para FreqAI.

        Target:
            `&s-up_or_down` = "up" si el retorno futuro supera 1%.
            `&s-up_or_down` = "down" en caso contrario.

        Args:
            dataframe: Velas OHLCV del par actual.
            metadata: Metadata del par.

        Returns:
            DataFrame con columna target `&s-up_or_down`.

        Nota:
            `self.freqai.class_names` es requerido por clasificadores FreqAI
            para mapear labels string a clases del modelo.
        """
        self.freqai.class_names = ["down", "up"]

        label_period = self.freqai_info["feature_parameters"]["label_period_candles"]
        future_return = dataframe["close"].shift(-label_period) / dataframe["close"] - 1
        dataframe["&s-up_or_down"] = np.where(future_return > 0.01, "up", "down")

        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Calcula indicadores tecnicos y ejecuta FreqAI.

        Args:
            dataframe: Velas OHLCV del par actual.
            metadata: Metadata del par.

        Returns:
            DataFrame con indicadores tecnicos y prediccion FreqAI.

        Importante:
            `self.freqai.start(...)` debe llamarse aqui, no en entry/exit.
        """
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema_regime"] = ta.EMA(dataframe, timeperiod=200)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        dataframe = self.freqai.start(dataframe, metadata, self)

        if "&s-up_or_down" in dataframe.columns and metadata.get("pair") == "BTC/USDT":
            distribution = dataframe["&s-up_or_down"].value_counts(normalize=True).to_dict()
            logger.info("FreqAI class distribution/prediction sample %s: %s", metadata.get("pair"), distribution)

        return dataframe

    @staticmethod
    def _do_predict_ok(dataframe: DataFrame):
        """
        Retorna mascara booleana para aceptar predicciones FreqAI.

        Args:
            dataframe: DataFrame retornado por `self.freqai.start(...)`.

        Returns:
            Serie booleana cuando existe `do_predict`; True si no existe.

        Regla oficial:
            `do_predict == 1` significa que la prediccion es confiable.
        """
        if "do_predict" in dataframe.columns:
            return dataframe["do_predict"] == 1
        return True

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Define entradas long con setup tecnico + confirmacion FreqAI.

        Args:
            dataframe: DataFrame con indicadores y prediccion FreqAI.
            metadata: Metadata del par.

        Returns:
            DataFrame con `enter_long` y `enter_tag` cuando aplica.
        """
        if "&s-up_or_down" not in dataframe.columns:
            return dataframe

        technical_setup = (
            (dataframe["ema_fast"] > dataframe["ema_slow"])
            & (dataframe["close"] > dataframe["ema_regime"])
            & (dataframe["rsi"] < 70)
        )

        ml_setup = self._do_predict_ok(dataframe) & (dataframe["&s-up_or_down"] == "up")

        dataframe.loc[
            technical_setup & ml_setup & (dataframe["volume"] > 0),
            ["enter_long", "enter_tag"],
        ] = (1, "tech_plus_freqai_up")

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Define salidas long por criterio tecnico o prediccion FreqAI bajista.

        Args:
            dataframe: DataFrame con indicadores y prediccion FreqAI.
            metadata: Metadata del par.

        Returns:
            DataFrame con `exit_long` y `exit_tag` cuando aplica.
        """
        technical_exit = (dataframe["ema_fast"] < dataframe["ema_slow"]) | (dataframe["rsi"] > 80)

        ml_exit = False
        if "&s-up_or_down" in dataframe.columns:
            ml_exit = self._do_predict_ok(dataframe) & (dataframe["&s-up_or_down"] == "down")

        dataframe.loc[
            technical_exit | ml_exit,
            ["exit_long", "exit_tag"],
        ] = (1, "tech_or_freqai_down")

        return dataframe
