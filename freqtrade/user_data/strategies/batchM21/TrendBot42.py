from pandas import DataFrame
from freqtrade.strategy import IStrategy
import talib.abstract as ta
class TrendBot42(IStrategy):
    def populate_indicators(self, df: DataFrame, metadata: dict) -> DataFrame:
        return df
    def populate_entry_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        return df
    def populate_exit_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        return df
