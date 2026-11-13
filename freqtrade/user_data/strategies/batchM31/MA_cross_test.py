from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta

from freqtrade.strategy.parameters import IntParameter

class MACross(IStrategy):
    can_short: bool = True
    timeframe = '1m'
    # set the initial stoploss to -10%
    stoploss = -0.0010

    # exit profitable positions at any time when the profit is greater than 1%
    minimal_roi = {"0": 0.0005}

    buy_SMA = IntParameter(20, 30, default=20, space='buy', optimize=False,load=False)
    buy_FMA = IntParameter(5, 30, default=10, space='buy', optimize=True)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # generate values for technical analysis indicators
        for val in self.buy_SMA.range:
            dataframe[f'slowMA_{val}'] = ta.SMA(dataframe, timeperiod=val)
        for val in self.buy_FMA.range:
            dataframe[f'fastMA_{val}'] = ta.SMA(dataframe, timeperiod=val)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # generate entry signals based on indicator values

        dataframe.loc[
            (dataframe[f'fastMA_{self.buy_FMA.value}'] > dataframe[f'slowMA_{self.buy_SMA.value}']),
            'enter_long'] = 1
        dataframe.loc[
            (dataframe[f'fastMA_{self.buy_FMA.value}'] < dataframe[f'slowMA_{self.buy_SMA.value}']),
            'enter_short'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # generate exit signals based on indicator values
        dataframe.loc[
            (dataframe[f'fastMA_{self.buy_FMA.value}'] < dataframe[f'slowMA_{self.buy_SMA.value}']),
            'exit_long'] = 1
        dataframe.loc[
            (dataframe[f'fastMA_{self.buy_FMA.value}'] > dataframe[f'slowMA_{self.buy_SMA.value}']),
            'exit_short'] = 1

        return dataframe
