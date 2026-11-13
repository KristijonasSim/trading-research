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


class PullbackStrategy(IStrategy):
    """
    Pullback-in-trend strategy (user spec).
    Entry: 1h EMA50 rising, price within 1% of EMA21, RSI crossed above 40 within last 3 candles,
           daily EMA20 > daily EMA50
    Exit: trailing stop (3% trail, activates after 4% gain), -3% stoploss
    """

    INTERFACE_VERSION = 3
    can_short: bool = False

    minimal_roi = {"0": 1.0}

    stoploss = -0.03
    trailing_stop = True
    trailing_stop_positive = 0.03
    trailing_stop_positive_offset = 0.04
    trailing_only_offset_is_reached = True
    use_custom_stoploss = False

    timeframe = "1h"
    startup_candle_count: int = 100
    process_only_new_candles = True
    use_exit_signal = False
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
        dataframe["ema21"]      = ta.EMA(dataframe, timeperiod=21)
        dataframe["ema50"]      = ta.EMA(dataframe, timeperiod=50)
        dataframe["rsi"]        = ta.RSI(dataframe, timeperiod=14)
        dataframe["volume_sma"] = ta.SMA(dataframe["volume"], timeperiod=20)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # RSI rose above 40 from below within last 3 candles
        rsi_cross_40 = (
            (dataframe["rsi"] > 40)
            & (
                (dataframe["rsi"].shift(1) < 40)
                | (dataframe["rsi"].shift(2) < 40)
                | (dataframe["rsi"].shift(3) < 40)
            )
        )

        dataframe.loc[
            (
                (dataframe["ema50"] > dataframe["ema50"].shift(1))  # EMA50 rising
                & (dataframe["close"] >= dataframe["ema21"] * 0.99) # within 1% of EMA21
                & (dataframe["close"] <= dataframe["ema21"] * 1.01)
                & rsi_cross_40
                & (dataframe["ema20_1d"] > dataframe["ema50_1d"])   # daily regime
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe
