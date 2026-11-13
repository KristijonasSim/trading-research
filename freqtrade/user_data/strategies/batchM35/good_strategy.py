from freqtrade.strategy import IStrategy
import talib.abstract as ta
import pandas as pd


class RsiReversionStrategy(IStrategy):
    timeframe = "15m"
    stoploss = -0.08
    minimal_roi = {"0": 0.06, "45": 0.03, "120": 0.01}
    startup_candle_count = 50

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["sma_50"] = ta.SMA(dataframe, timeperiod=50)
        return dataframe

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        dataframe.loc[
            (dataframe["rsi"] < 30) & (dataframe["close"] > dataframe["sma_50"]),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        dataframe.loc[dataframe["rsi"] > 70, "exit_long"] = 1
        return dataframe
