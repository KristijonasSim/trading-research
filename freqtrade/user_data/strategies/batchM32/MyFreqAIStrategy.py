from freqtrade.strategy import IStrategy
from freqtrade.freqai.prediction_models.LightGBMRegressor import LightGBMRegressor
import pandas_ta as ta

class MyFreqAIStrategy(IStrategy):
    INTERFACE_VERSION = 3  # For Freqtrade compatibility
    minimal_roi = {"0": 0.05}  # 5% profit target
    stoploss = -0.02  # 2% stop-loss
    timeframe = '1h'  # 1-hour data

    def populate_indicators(self, dataframe, metadata):
        dataframe['rsi'] = ta.rsi(dataframe['close'], length=14)
        return dataframe

    def populate_entry_trend(self, dataframe, metadata):
        conditions = (dataframe['rsi'] < 30) & (dataframe['freqai_prediction'] > 0.5)
        dataframe.loc[conditions, 'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe, metadata):
        conditions = (dataframe['rsi'] > 70) | (dataframe['freqai_prediction'] < 0.5)
        dataframe.loc[conditions, 'exit_long'] = 1
        return dataframe

    def freqai_models(self):
        return {"regressor": LightGBMRegressor}  # Auto-ML model
