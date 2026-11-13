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


class RsiReversion(IStrategy):
    """
    Mean-reversion strategy using RSI.

    Buys when RSI is oversold (< 30) and starts to turn up.
    Sells when RSI is overbought (> 70).

    Minimal template — adjust thresholds to your liking.
    """

    # --- ROI / Stoploss ---
    minimal_roi = {
        "0": 0.08,
        "30": 0.04,
        "60": 0.02,
        "120": 0
    }

    stoploss = -0.08

    # --- Trailing stop ---
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True

    # --- Timeframe ---
    timeframe = "15m"

    # --- Buy / Sell signals ---
    use_sell_signal = True
    sell_profit_only = False
    process_only_new_candles = True

    # --- Startup candles ---
    startup_candle_count = 50

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = [
            (dataframe["rsi"] < 30),
            (dataframe["rsi"] > dataframe["rsi"].shift(1)),  # RSI turning up
            (dataframe["volume"] > 0)
        ]

        dataframe.loc[
            reduce(lambda x, y: x & y, conditions),
            "buy"
        ] = 1

        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = [
            (dataframe["rsi"] > 70),
            (dataframe["volume"] > 0)
        ]

        dataframe.loc[
            reduce(lambda x, y: x & y, conditions),
            "sell"
        ] = 1

        return dataframe