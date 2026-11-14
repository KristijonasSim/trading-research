"""Minimal SMA crossover baseline for V2 dry-run / paper testing."""

from __future__ import annotations

import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IStrategy


class BaselineStrategy(IStrategy):
    INTERFACE_VERSION = 3

    minimal_roi = {"0": 0.05, "30": 0.02, "60": 0.01, "120": 0}
    stoploss = -0.10
    timeframe = "5m"

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["sma_fast"] = ta.SMA(dataframe, timeperiod=10)
        dataframe["sma_slow"] = ta.SMA(dataframe, timeperiod=30)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["sma_fast"] > dataframe["sma_slow"]) & (dataframe["volume"] > 0),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe["sma_fast"] < dataframe["sma_slow"]), "exit_long"] = 1
        return dataframe
