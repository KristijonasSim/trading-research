# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# --- Do not remove these libs ---
import numpy as np  # noqa
import pandas as pd  # noqa
from pandas import DataFrame
from freqtrade.strategy import IStrategy
from functools import reduce

# --------------------------------
# Add your lib to import here
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib


class MovingAverageCross(IStrategy):
    """
    Simple Moving Average Crossover strategy.

    Buys when fast EMA crosses above slow EMA.
    Sells when fast EMA crosses below slow EMA.

    This is a minimal template — extend with your own logic.
    """

    # --- ROI / Stoploss ---
    minimal_roi = {
        "0": 0.05,
        "30": 0.02,
        "60": 0.01,
        "120": 0
    }

    stoploss = -0.05

    # --- Trailing stop ---
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02
    trailing_only_offset_is_reached = True

    # --- Timeframe ---
    timeframe = "5m"

    # --- Buy / Sell signals ---
    use_sell_signal = True
    sell_profit_only = False
    process_only_new_candles = True

    # --- Startup candles ---
    startup_candle_count = 100

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Fast & Slow EMA
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=10)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=50)

        # Optional: RSI for confirmation
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = [
            qtpylib.crossed_above(dataframe["ema_fast"], dataframe["ema_slow"]),
            dataframe["volume"] > 0
        ]

        dataframe.loc[
            reduce(lambda x, y: x & y, conditions),
            "buy"
        ] = 1

        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = [
            qtpylib.crossed_below(dataframe["ema_fast"], dataframe["ema_slow"]),
            dataframe["volume"] > 0
        ]

        dataframe.loc[
            reduce(lambda x, y: x & y, conditions),
            "sell"
        ] = 1

        return dataframe