"""Пример скальпинговой стратегии — для демонстрации классификации."""

from pandas import DataFrame
from freqtrade.strategy import IStrategy
import talib.abstract as ta


class EliteScalper5m(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "5m"
    stoploss = -0.03
    minimal_roi = {"0": 0.02, "15": 0.01, "30": 0}

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=8)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=21)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["ema_fast"] > dataframe["ema_slow"]),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["ema_fast"] < dataframe["ema_slow"]),
            "exit_long",
        ] = 1
        return dataframe
