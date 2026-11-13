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


class BreakoutRetestStrategy(IStrategy):
    """
    Breakout + Retest strategy.
    Wait for price to break above N-bar resistance, then buy the pullback/retest of that level.

    VARIANT PARAMS:
      LOOKBACK        = 20 | 30       -- candles for rolling resistance high
      RETEST_BAND     = 0.02 | 0.03   -- how close to resistance counts as retest
      BREAKOUT_WINDOW = 5 | 3         -- candles back to look for the breakout
      RSI_MIN         = 45 | 40       -- minimum RSI during retest
      VOLUME_MULT     = 1.2 | 1.0     -- volume requirement on retest candle
    """

    # --- VARIANT PARAMS ---
    LOOKBACK        = 20
    RETEST_BAND     = 0.02
    BREAKOUT_WINDOW = 5
    RSI_MIN         = 45
    VOLUME_MULT     = 1.2
    # ----------------------

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
        dataframe["ema50"]      = ta.EMA(dataframe, timeperiod=50)
        dataframe["rsi"]        = ta.RSI(dataframe, timeperiod=14)
        dataframe["adx"]        = ta.ADX(dataframe, timeperiod=14)
        dataframe["volume_sma"] = ta.SMA(dataframe["volume"], timeperiod=20)

        # Resistance: rolling high of last LOOKBACK candles, shifted so it excludes current candle
        dataframe["resistance"] = dataframe["high"].shift(1).rolling(self.LOOKBACK).max()

        # Breakout: close was above resistance within the last BREAKOUT_WINDOW candles
        broke = pd.Series(False, index=dataframe.index)
        for i in range(1, self.BREAKOUT_WINDOW + 1):
            broke = broke | (dataframe["close"].shift(i) > dataframe["resistance"].shift(i))
        dataframe["recent_breakout"] = broke

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        b = self.RETEST_BAND
        cond = (
            dataframe["recent_breakout"]                               # breakout happened recently
            & (dataframe["close"] >= dataframe["resistance"] * (1-b)) # price is retesting the level
            & (dataframe["close"] <= dataframe["resistance"] * (1+b))
            & (dataframe["close"] > dataframe["open"])                 # bullish candle on retest
            & (dataframe["rsi"] > self.RSI_MIN)                       # not oversold
            & (dataframe["adx"] > 20)                                  # some trend present
            & (dataframe["volume"] > dataframe["volume_sma"] * self.VOLUME_MULT)
            & (dataframe["ema20_1d"] > dataframe["ema50_1d"])         # daily regime
            & (dataframe["close"] > dataframe["ema50_1d"])
        )
        dataframe.loc[cond, "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe
