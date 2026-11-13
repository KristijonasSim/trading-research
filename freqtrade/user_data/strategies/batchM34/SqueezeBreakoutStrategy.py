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


class SqueezeBreakoutStrategy(IStrategy):
    """
    Volatility-expansion (TTM Squeeze) strategy.

    Thesis
    ------
    When the Bollinger Bands contract INSIDE the Keltner Channels, realised
    volatility is compressed and price energy is coiling. The tradable edge is
    not the squeeze itself but the EXPANSION that follows it. We enter when the
    squeeze RELEASES (BBs push back outside the KCs) and the TTM momentum
    oscillator confirms an upward thrust.

    The primary entry trigger is a volatility-state change (BB/KC relationship),
    not a moving-average crossover. The daily EMA pair is used ONLY as a
    higher-timeframe regime gate, to keep this long-only spot book aligned with
    the macro trend and out of low-conviction chop.

    Hyperopt
    --------
    All entry thresholds are exposed as Int/Decimal/Boolean parameters so the
    strategy can be tuned via `freqtrade hyperopt`.
    """

    INTERFACE_VERSION = 3
    can_short: bool = False

    timeframe = "1h"
    startup_candle_count: int = 400
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    minimal_roi = {"0": 0.25}
    stoploss = -0.06
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True
    use_custom_stoploss = False

    order_types = {
        "entry": "limit", "exit": "limit",
        "stoploss": "market", "stoploss_on_exchange": False,
    }
    order_time_in_force = {"entry": "GTC", "exit": "GTC"}

    # --- Hyperopt spaces ---------------------------------------------------
    bb_period   = IntParameter(15, 30, default=20, space="buy", optimize=True)
    bb_std      = DecimalParameter(1.6, 2.6, default=2.0, decimals=1, space="buy", optimize=True)
    kc_period   = IntParameter(15, 30, default=20, space="buy", optimize=True)
    kc_mult     = DecimalParameter(1.0, 2.5, default=1.5, decimals=1, space="buy", optimize=True)
    mom_period  = IntParameter(8, 24, default=12, space="buy", optimize=True)
    fire_window = IntParameter(1, 6, default=3, space="buy", optimize=True)
    atr_floor   = DecimalParameter(0.0, 2.0, default=0.3, decimals=1, space="buy", optimize=True)

    mom_exit    = BooleanParameter(default=False, space="sell", optimize=True)

    @informative('1d')
    def populate_indicators_1d(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['ema50']  = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema200'] = ta.EMA(dataframe, timeperiod=200)
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        bb_p = int(self.bb_period.value)
        kc_p = int(self.kc_period.value)
        mom_p = int(self.mom_period.value)

        # Bollinger Bands
        bb = ta.BBANDS(dataframe, timeperiod=bb_p,
                       nbdevup=self.bb_std.value, nbdevdn=self.bb_std.value)
        dataframe["bb_upper"] = bb["upperband"]
        dataframe["bb_lower"] = bb["lowerband"]

        # Keltner Channels (EMA midline +/- ATR multiple)
        kc_mid = ta.EMA(dataframe, timeperiod=kc_p)
        atr = ta.ATR(dataframe, timeperiod=kc_p)
        dataframe["kc_upper"] = kc_mid + self.kc_mult.value * atr
        dataframe["kc_lower"] = kc_mid - self.kc_mult.value * atr
        dataframe["atr_pct"] = atr / dataframe["close"] * 100.0

        # Squeeze state: BBs fully inside the Keltner Channels
        squeeze_on = (
            (dataframe["bb_upper"] < dataframe["kc_upper"])
            & (dataframe["bb_lower"] > dataframe["kc_lower"])
        )
        dataframe["squeeze_on"] = squeeze_on
        # Squeeze "fired" this candle: was compressed last candle, released now
        dataframe["squeeze_fired"] = squeeze_on.shift(1).fillna(False) & (~squeeze_on)

        # TTM momentum oscillator: linear regression of price vs a
        # blended midline (Donchian mid + SMA close)
        donchian_mid = (
            dataframe["high"].rolling(mom_p).max()
            + dataframe["low"].rolling(mom_p).min()
        ) / 2.0
        sma_close = ta.SMA(dataframe, timeperiod=mom_p)
        ref = (donchian_mid + sma_close) / 2.0
        dataframe["mom"] = ta.LINEARREG(dataframe["close"] - ref, timeperiod=mom_p)
        dataframe["mom_prev"] = dataframe["mom"].shift(1)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        fw = int(self.fire_window.value)
        # A squeeze released within the last `fire_window` candles
        recently_fired = (
            dataframe["squeeze_fired"].rolling(fw).max().fillna(0) > 0
        )

        dataframe.loc[
            (
                recently_fired                                       # volatility expansion event
                & (~dataframe["squeeze_on"])                         # not re-compressed
                & (dataframe["close"] > dataframe["bb_upper"])      # decisive 2-std upside breakout
                & (dataframe["mom"] > 0)                             # momentum confirms direction
                & (dataframe["atr_pct"] > self.atr_floor.value)     # live tape, not dead chop
                & (dataframe["ema50_1d"] > dataframe["ema200_1d"])  # daily regime: macro uptrend
                & (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        if self.mom_exit.value:
            dataframe.loc[
                (dataframe["mom"] < 0) & (dataframe["mom"] < dataframe["mom_prev"]),
                "exit_long",
            ] = 1
        return dataframe
