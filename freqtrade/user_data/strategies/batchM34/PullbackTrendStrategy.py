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


class PullbackTrendStrategy(IStrategy):
    """
    Pullback-in-trend strategy.
    Daily regime filter keeps us in bull markets only.
    1h entry: trend intact (EMAs aligned), price pulls back to EMA zone,
    RSI resets and turns back up, bullish candle confirms resumption.

    VARIANT PARAMS (change between test runs):
      PULLBACK_EMA        = "ema21"  | "ema50"   -- which EMA is the pullback target
      PULLBACK_BAND       = 0.02     | 0.03       -- % tolerance around that EMA
      RSI_LOW             = 40       | 35         -- minimum RSI (not oversold)
      RSI_HIGH            = 65       | 55         -- maximum RSI (not yet extended)
      REQUIRE_RSI_TURNING = True     | False      -- RSI must be rising this candle
      VOLUME_MULT         = 1.5      | 1.0        -- minimum volume multiplier
    """

    # --- VARIANT PARAMS (edit these between runs) ---
    PULLBACK_EMA        = "ema50"
    PULLBACK_BAND       = 0.03
    RSI_LOW             = 35
    RSI_HIGH            = 55
    REQUIRE_RSI_TURNING = True
    VOLUME_MULT         = 1.0
    # -------------------------------------------------

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
        dataframe["ema9"]       = ta.EMA(dataframe, timeperiod=9)
        dataframe["ema21"]      = ta.EMA(dataframe, timeperiod=21)
        dataframe["ema50"]      = ta.EMA(dataframe, timeperiod=50)
        dataframe["rsi"]        = ta.RSI(dataframe, timeperiod=14)
        dataframe["rsi_prev"]   = dataframe["rsi"].shift(1)
        dataframe["adx"]        = ta.ADX(dataframe, timeperiod=14)
        dataframe["volume_sma"] = ta.SMA(dataframe["volume"], timeperiod=20)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        target = dataframe[self.PULLBACK_EMA]
        b = self.PULLBACK_BAND

        cond = (
            (dataframe["ema9"] > dataframe["ema21"])           # short-term trend up
            & (dataframe["ema21"] > dataframe["ema50"])        # medium-term trend up
            & (dataframe["close"] >= target * (1 - b))        # pulled back to target EMA
            & (dataframe["close"] <= target * (1 + b))
            & (dataframe["close"] > dataframe["open"])         # bullish candle resuming
            & (dataframe["rsi"] > self.RSI_LOW)
            & (dataframe["rsi"] < self.RSI_HIGH)
            & (dataframe["adx"] > 20)
            & (dataframe["volume"] > dataframe["volume_sma"] * self.VOLUME_MULT)
            & (dataframe["ema20_1d"] > dataframe["ema50_1d"]) # daily regime
            & (dataframe["close"] > dataframe["ema50_1d"])
        )
        if self.REQUIRE_RSI_TURNING:
            cond = cond & (dataframe["rsi"] > dataframe["rsi_prev"])

        dataframe.loc[cond, "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe
