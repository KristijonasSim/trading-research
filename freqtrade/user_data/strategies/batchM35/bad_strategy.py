from freqtrade.strategy import IStrategy
import talib.abstract as ta
import pandas as pd


class my_bot(IStrategy):            # not PascalCase -> warning
    timeframe = "5m"
    stoploss = -0.05

    def populate_indicators(self, dataframe, metadata):
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe, metadata):
        dataframe.loc[dataframe["rsi"] < 30, "enter_long"] = 1
        return dataframe
    # populate_exit_trend missing -> error
