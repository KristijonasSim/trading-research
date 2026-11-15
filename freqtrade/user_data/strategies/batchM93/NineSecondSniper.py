from freqtrade.strategy import IStrategy
from pandas import DataFrame
import pandas as pd
import talib.abstract as ta
from datetime import datetime
import numpy as np


class NineSecondSniper(IStrategy):
    """
    9秒狙击手策略 - 真实实现

    核心逻辑：
    - SAR指标为核心找反转点
    - 激进用法：在SAR压制价格时做多，赌突破
    - 9秒价格对比动能判断
    - 仓位减半机制
    - 动态止损和模糊止盈
    """

    timeframe = '1m'
    max_open_trades = 1
    stake_amount = 100
    startup_candle_count = 50

    minimal_roi = {
        "0": 0.01,     # 赚够就平仓
        "60": 0.005,   # 模糊止盈
    }

    stoploss = -0.05  # 默认止损，但实际由custom_exit控制
    trailing_stop = False  # 不使用追踪止损

    order_types = {
        'entry': 'market',
        'exit': 'market',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    unfilledtimeout = {
        'entry': 10,
        'exit': 10,
        'unit': 'seconds'
    }

    leverage_config = {
        'BTC/USDT:USDT': 8.0,   # 恢复保守杠杆配置
        'ETH/USDT:USDT': 6.0,
        'SOL/USDT:USDT': 5.0,
        'XRP/USDT:USDT': 4.0,
        'DOGE/USDT:USDT': 4.0
    }

    # 9秒价格缓冲区（环形缓冲区）
    price_buffer_size = 9
    price_buffers = {}  # 为每个交易对维护缓冲区

    def informative_pairs(self) -> list:
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        pair = metadata['pair']

        # SAR指标 - 恢复标准参数
        df['sar'] = ta.SAR(df['high'].values, df['low'].values,
                          acceleration=0.02, maximum=0.2)

        # SAR压制判断：价格在SAR下方
        df['sar_suppression'] = df['close'] < df['sar']

        # 9秒价格对比（当前价格 vs 9秒前价格）
        df['price_9sec_ago'] = df['close'].shift(9)  # 9根K线前 = 9分钟 ≈ 9秒概念
        df['price_change_9sec'] = (df['close'] - df['price_9sec_ago']) / df['price_9sec_ago']

        # 波动幅度要求（动能判断）
        df['volatility_9sec'] = abs(df['price_change_9sec'])

        # 成交量确认
        df['volume_sma'] = ta.SMA(df['volume'].values, timeperiod=10)
        df['volume_ratio'] = df['volume'] / df['volume_sma']

        # 环形缓冲区维护（模拟代码的高级设计）
        if pair not in self.price_buffers:
            self.price_buffers[pair] = np.zeros(self.price_buffer_size)

        # 更新缓冲区（存储最近9秒价格）
        buffer = self.price_buffers[pair]
        for i in range(len(df)):
            if i >= self.price_buffer_size:
                # 环形缓冲区逻辑： oldest -> newest
                buffer[:-1] = buffer[1:]
                buffer[-1] = df['close'].iloc[i]

        # 从缓冲区计算9秒动量
        df['buffer_momentum'] = 0.0
        if len(buffer) >= self.price_buffer_size:
            df['buffer_momentum'] = (buffer[-1] - buffer[0]) / buffer[0]

        return df

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 current_profit: float = 0.0, min_stops: float = 0.0,
                 max_stops: float = 0.0, current_time_rows: DataFrame = None,
                 **kwargs) -> float:
        base_leverage = self.leverage_config.get(pair, 5.0)

        # 恢复仓位减半机制：盈利时自动减半仓位（降低风险）
        if current_profit > 0.005:  # 0.5%盈利就开始减仓
            base_leverage *= 0.5  # 减半杠杆

        return min(base_leverage, 15.0)

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        df['enter_long'] = 0

        if len(df) < self.startup_candle_count:
            return df

        # 9秒狙击手核心逻辑 - 平衡参数
        sniper_conditions = (
            # SAR指标核心：价格被SAR压制（激进做多）
            df['sar_suppression'] &  # SAR在价格上方压制
            # 9秒动能判断：恢复合理波动要求
            (df['volatility_9sec'] > 0.0015) &  # 9秒内波动>0.15% (中等)
            (df['price_change_9sec'] > 0.0008) &  # 9秒内上涨>0.08% (中等)
            # 成交量确认：合理要求
            (df['volume_ratio'] > 1.4) &  # 成交量1.4倍 (中等)
            # 缓冲区动量确认：合理标准
            (df['buffer_momentum'] > 0.0008)  # 合理动量要求
        )

        df.loc[sniper_conditions, 'enter_long'] = 1

        return df

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        df['exit'] = 0

        # SAR反转：SAR跌破价格（原压制失效）
        df.loc[df['close'] > df['sar'], 'exit'] = 1

        # 9秒动量反转
        df.loc[df['price_change_9sec'] < -0.001, 'exit'] = 1

        return df

    def custom_exit(self, pair: str, current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs) -> bool:
        """
        显著风控缺陷：无预设止损，要等浮亏扩大且动能恶化时才设置
        止盈也无具体点位，只设定赚够目标金额就平仓

        优化：调整阈值以平衡风险收益
        """

        # 止盈：赚够目标金额就平仓（模糊标准）- 更激进
        if current_profit > 0.012:  # 1.2%利润就平仓 (更快获利)
            return True

        # 止损：等浮亏扩大且动能恶化时才设置（被动止损）
        # 优化：稍微提前止损
        if current_profit < -0.012:  # -1.2%止损 (稍微提前)
            return True

        return False
