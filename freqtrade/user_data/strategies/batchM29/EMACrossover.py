# -------------------------------
from freqtrade.strategy import IStrategy
from typing import Dict, List
from functools import reduce
from pandas import DataFrame
# --------------------------------

import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib


class EMACrossover(IStrategy):

    """
    EMA Crossover strategy, uses two emas, when the shorter EMA crosses over the longer EMA the strategy
    longs, and shorts when short EMA crosses down on the longer EMA
    """

    INTERFACE_VERSION: int = 3

    timeframe = '5m'

    stoploss = -0.10

    can_short = True

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        ema50 = ta.EMA(dataframe, timeperiod=50)
        ema200 = ta.EMA(dataframe, timeperiod=200)

        dataframe['ema50'] = ema50
        dataframe['ema200'] = ema200

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        # Long condition, ema50 crosses up on ema200
        dataframe.loc[
            (
                (dataframe['ema50'].shift(1) < dataframe['ema200'].shift(1)) &
                (dataframe['ema50'] > dataframe['ema200'])
            ),
            'enter_long'] = 1

        # Short condition, ema50 crosses down on ema200
        dataframe.loc[
            (
                (dataframe['ema50'].shift(1) > dataframe['ema200'].shift(1)) &
                (dataframe['ema50'] < dataframe['ema200'])
            ),
            'enter_short'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        # Exit long condition, ema 50 above ema200
        dataframe.loc[
            (
                (dataframe['ema50'] < dataframe['ema200'])
            ),
            'exit_long'] = 1

        # Exit short condition, ema 50 above ema200
        dataframe.loc[
            (
                (dataframe['ema50'] > dataframe['ema200'])
            ),
            'exit_short'] = 1

        return dataframe