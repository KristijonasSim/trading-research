# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# --- Do not remove these libs ---
import numpy as np  # noqa
import pandas as pd  # noqa
from pandas import DataFrame
from freqtrade.strategy import IStrategy, DecimalParameter, IntParameter
from functools import reduce

# --------------------------------
# Add your lib to import here
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib


class BinanceScalper(IStrategy):
    """
    Bollinger Band + RSI mean-reversion scalper.

    Designed for low-capital Binance spot trading (~$10 per trade).

    - Timeframe 1m for fast entries/exits.
    - Enters long when price touches the lower Bollinger Band AND RSI is
      oversold, expecting a bounce back to the band midline.
    - Exits when price reclaims the midline OR RSI is no longer oversold.
    - Hard stoploss below the band protects against strong downtrends.
    - Minimal ROI ladder favors quick small wins, scaling down over time.

    Notes
    -----
    * Set `stake_amount = 10` (USD) in the user's config to keep position size
      small.
    * Pair whitelist should be liquid majors (BTC/USDT, ETH/USDT, SOL/USDT)
      to ensure fills at the desired price.
    * Use `process_only_new_candles = True` (below) to avoid duplicate signals
      on the same candle.
    """

    INTERFACE_VERSION = 3

    # --- Hyperoptable parameters ---
    bb_period = IntParameter(10, 40, default=20, space="buy")
    bb_std = DecimalParameter(1.5, 3.0, default=2.0, space="buy")
    rsi_period = IntParameter(7, 21, default=14, space="buy")
    rsi_buy = IntParameter(15, 35, default=25, space="buy")
    rsi_exit = IntParameter(40, 70, default=55, space="sell")

    # --- ROI / Stoploss ---
    # Quick-scalp ladder: take small profits early, scale down over time.
    minimal_roi = {
        "0": 0.012,   # 1.2% immediately
        "10": 0.006,  # 0.6% after 10 minutes
        "30": 0.003,  # 0.3% after 30 minutes
        "60": 0.0
    }

    # Stoploss below the lower Bollinger Band.
    stoploss = -0.025

    # --- Trailing stop ---
    trailing_stop = True
    trailing_stop_positive = 0.004
    trailing_stop_positive_offset = 0.008
    trailing_only_offset_is_reached = True

    # --- Timeframe ---
    timeframe = "1m"

    # --- Buy / Sell signals ---
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    process_only_new_candles = True

    # --- Startup candles ---
    # Need enough 1m candles to compute longest indicator (bb_period=40 max).
    startup_candle_count = 60

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        period = self.bb_period.value
        std = self.bb_std.value
        rsi_p = self.rsi_period.value

        # Bollinger Bands
        bollinger = qtpylib.bollinger_bands(
            dataframe["close"], window=period, stds=std
        )
        dataframe["bb_lower"] = bollinger["lower"]
        dataframe["bb_middle"] = bollinger["mid"]
        dataframe["bb_upper"] = bollinger["upper"]

        # RSI
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=rsi_p)

        # Volume SMA - filter out dead candles
        dataframe["volume_sma"] = ta.SMA(dataframe, timeperiod=20)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = [
            # Price touched (or dipped below) the lower Bollinger Band.
            dataframe["close"] <= dataframe["bb_lower"],
            # RSI is oversold -> expect bounce.
            dataframe["rsi"] < self.rsi_buy.value,
            # Volume filter - skip illiquid candles.
            dataframe["volume"] > dataframe["volume_sma"],
            # Make sure the candle is not flat / missing.
            dataframe["volume"] > 0,
        ]

        dataframe.loc[
            reduce(lambda x, y: x & y, conditions),
            "enter_long"
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = [
            # Mean reversion target reached - price back at midline.
            dataframe["close"] >= dataframe["bb_middle"],
            # RSI cooled off - momentum neutralized.
            dataframe["rsi"] > self.rsi_exit.value,
            dataframe["volume"] > 0,
        ]

        dataframe.loc[
            reduce(lambda x, y: x & y, conditions),
            "exit_long"
        ] = 1

        return dataframe
