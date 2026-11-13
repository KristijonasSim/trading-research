# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
import numpy as np
import pandas as pd
from datetime import datetime
from pandas import DataFrame
from typing import Optional

from freqtrade.strategy import (
    IStrategy, informative,
    IntParameter, DecimalParameter, BooleanParameter,
)
import talib.abstract as ta


class BandFadeStrategy(IStrategy):
    """
    Extreme mean-reversion (liquidation fade) strategy.

    Thesis
    ------
    Sharp 2-standard-deviation downside dislocations in crypto are frequently
    liquidation-driven: forced selling overshoots fair value and snaps back.
    The edge is fading that overshoot. We buy when price pierces the LOWER
    Bollinger Band while oversold, but ONLY inside a confirmed daily uptrend --
    i.e. we buy dips in a bull market, never catch a falling knife in a bear.

    The primary entry trigger is a standard-deviation extreme (a statistical
    anomaly), not a moving-average crossover. The daily EMA pair is used only
    as a regime gate. Exit targets reversion to the mean (BB midline).

    Companion to SqueezeBreakoutStrategy: 4 structural iterations showed that
    chasing the upper-band breakout buys local tops and loses even in a +470%
    market. This strategy tests the inverse hypothesis.
    """

    INTERFACE_VERSION = 3
    can_short: bool = False

    timeframe = "1h"
    startup_candle_count: int = 400
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    minimal_roi = {"0": 0.06}
    stoploss = -0.05
    trailing_stop = False
    use_custom_stoploss = False

    order_types = {
        "entry": "limit", "exit": "limit",
        "stoploss": "market", "stoploss_on_exchange": False,
    }
    order_time_in_force = {"entry": "GTC", "exit": "GTC"}

    # --- Hyperopt spaces ---------------------------------------------------
    bb_period   = IntParameter(15, 30, default=20, space="buy", optimize=True)
    bb_std      = DecimalParameter(1.8, 3.0, default=2.0, decimals=1, space="buy", optimize=True)
    rsi_period  = IntParameter(8, 21, default=14, space="buy", optimize=True)
    rsi_buy     = IntParameter(20, 40, default=30, space="buy", optimize=True)
    cascade_atr = DecimalParameter(1.0, 4.0, default=2.0, decimals=1, space="buy", optimize=True)

    @informative('1d')
    def populate_indicators_1d(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['ema50']  = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema200'] = ta.EMA(dataframe, timeperiod=200)
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        bb_p = int(self.bb_period.value)

        bb = ta.BBANDS(dataframe, timeperiod=bb_p,
                       nbdevup=self.bb_std.value, nbdevdn=self.bb_std.value)
        dataframe["bb_upper"] = bb["upperband"]
        dataframe["bb_mid"]   = bb["middleband"]
        dataframe["bb_lower"] = bb["lowerband"]

        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=int(self.rsi_period.value))

        # Cascade detection: how far price has dropped from the 24h high, in ATRs
        dataframe["atr"]  = ta.ATR(dataframe, timeperiod=14)
        dataframe["hi24"] = dataframe["high"].rolling(24).max()
        dataframe["drop_atr"] = (dataframe["hi24"] - dataframe["close"]) / dataframe["atr"]
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["close"] < dataframe["bb_lower"])        # 2-std downside extreme
                & (dataframe["rsi"] < self.rsi_buy.value)           # oversold
                & (dataframe["drop_atr"] > self.cascade_atr.value)  # genuine fast cascade, not a routine dip
                & (dataframe["close"] > dataframe["open"])          # bounce is starting, not still falling
                & (dataframe["ema50_1d"] > dataframe["ema200_1d"])  # daily regime: macro uptrend
                & (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["close"] > dataframe["bb_mid"]),             # reverted to the mean
            "exit_long",
        ] = 1
        return dataframe
