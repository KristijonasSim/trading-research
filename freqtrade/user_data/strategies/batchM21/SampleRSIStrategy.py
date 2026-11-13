"""Пример стратегии для проверки KERRIGAN Trading Lab."""

from pandas import DataFrame
from freqtrade.strategy import IStrategy
import talib.abstract as ta


class SampleRSIStrategy(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "5m"
    stoploss = -0.10
    minimal_roi = {"0": 0.05, "30": 0.02, "60": 0}

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["rsi"] < 30),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["rsi"] > 70),
            "exit_long",
        ] = 1
        return dataframe
