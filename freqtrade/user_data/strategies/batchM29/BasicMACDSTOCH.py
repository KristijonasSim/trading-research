# -------------------------------
from freqtrade.strategy import IStrategy
from pandas import DataFrame
# --------------------------------

import talib.abstract as ta

class BasicMACDSTOCH(IStrategy):


    timeframe = '5m'
    stoploss = -0.10

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        # MACD settings
        macd = ta.MACD(dataframe, fastperiod=12, slowperiod=26, signalperiod=9)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']

        # Stochastic settings
        stoch = ta.STOCH(dataframe, fastk_period=5, slowk_period=3, slowk_matype=0, slowd_period=3,
                                slowd_matype=0)
        dataframe['slowk'] = stoch['slowk']
        dataframe['slowd'] = stoch['slowd']
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        # TODO: Improve logic on this strategy so it enters only on crossovers and also add macd part of strat
        dataframe.loc[
            (
                (dataframe['slowk'] < 20) &
                (dataframe['slowd'] < 20) &
                (dataframe['slowk'].shift(1) < dataframe['slowd'].shift(1)) &
                (dataframe['slowk'] > dataframe['slowd']) &
                (dataframe['macdhist'] > 0)
                # (dataframe['macd'] > dataframe['macdsignal']),
            ),
            'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        # TODO: Improve logic on this strategy so it exits only on crossovers and also add macd part of strat
        dataframe.loc[
            (
                (dataframe['slowk'] > 80) &
                (dataframe['slowd'] > 80) &
                (dataframe['slowk'] < dataframe['slowd']) &
                (dataframe['slowk'].shift(1) > dataframe['slowd'].shift(1))
            ),
            'exit_long'] = 1

        return dataframe