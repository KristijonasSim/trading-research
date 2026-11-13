import numpy as np
from freqtrade.strategy import IStrategy
from pandas import DataFrame
import random

class MockPreviewStrategy(IStrategy):
    """
    PM 专用 Mock 策略：
    目的是为了让 UI 动起来，展示各种盈亏状态。
    逻辑：随机买入，持仓 2 分钟后随机卖出。
    """
    INTERFACE_VERSION = 3
    timeframe = '1m'
    
    # 极小的 ROI 确保快速成交显示
    minimal_roi = { "0": 0.01 }
    stoploss = -0.05

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 生成一些假指标供图表显示
        dataframe['rsi'] = np.random.randint(20, 80, size=len(dataframe))
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 30% 的概率触发买入，确保所有币种快速开仓
        dataframe.loc[
            (dataframe['volume'] > 0) & 
            (dataframe['rsi'] < 90), # 几乎总是 True
            'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 50% 的概率触发卖出
        dataframe.loc[
            (dataframe['volume'] > 0) & 
            (dataframe['rsi'] > 10), 
            'exit_long'] = 1
        return dataframe