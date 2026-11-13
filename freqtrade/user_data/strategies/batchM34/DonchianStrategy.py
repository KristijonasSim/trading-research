# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from pandas import DataFrame
from typing import Optional, Union

from freqtrade.strategy import (
    IStrategy, Trade, Order, PairLocks, informative,
    timeframe_to_minutes, merge_informative_pair,
    stoploss_from_absolute, stoploss_from_open,
)
import talib.abstract as ta
from technical import qtpylib


class DonchianStrategy(IStrategy):
    """
    Donchian/Turtle-style breakout strategy (user spec).
    Entry:  Close > 20-period high (excluding current candle)
            AND daily EMA20 > daily EMA50
    Exit:   Close < 10-period low (excluding current candle)
            OR -5% stoploss
    No trailing stop. Classic trend-following entry/exit.
    """

    INTERFACE_VERSION = 3
    can_short: bool = False

    minimal_roi = {"0": 1.0}

    stoploss = -0.05
    trailing_stop = False
    use_custom_stoploss = False

    timeframe = "1h"
    startup_candle_count: int = 100
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    order_types = {
        "entry": "limit", "exit": "limit",
        "stoploss": "market", "stoploss_on_exchange": False,
    }
    order_time_in_force = {"entry": "GTC", "exit": "GTC"}

    @informative('1d')
    def populate_indicators_1d(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['ema20'] = ta.EMA(dataframe, timeperiod=20)
        dataframe['ema50'] = ta.EMA(dataframe, timeperiod=50)
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Donchian channels — shift(1) to exclude the current candle
        dataframe["dc_high20"] = dataframe["high"].shift(1).rolling(20).max()
        dataframe["dc_low10"]  = dataframe["low"].shift(1).rolling(10).min()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["close"] > dataframe["dc_high20"])     # new 20-bar high breakout
                & (dataframe["ema20_1d"] > dataframe["ema50_1d"]) # daily regime filter
                & (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["close"] < dataframe["dc_low10"]),         # close below 10-bar low
            "exit_long",
        ] = 1
        return dataframe
