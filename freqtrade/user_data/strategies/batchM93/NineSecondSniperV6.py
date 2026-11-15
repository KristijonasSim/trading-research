from freqtrade.strategy import IStrategy
from pandas import DataFrame
import pandas as pd
import talib.abstract as ta
from datetime import datetime
import numpy as np


class NineSecondSniperV6(IStrategy):
    """
    9秒狙击手策略 V6 - 移除止损版

    V6 核心改进：
    1. 移除固定止损 - SAR 压制作为主要出场信号
    2. 提高 ROI 止盈 - 3%-5% 给趋势更多空间
    3. 优化 SAR 信号 - 添加波动率和 ATR 过滤
    4. 严格入场 - 只在高质量 SAR 转向时入场
    """

    timeframe = '1m'
    max_open_trades = 2
    stake_amount = 100
    startup_candle_count = 100

    # V6 核心：提高 ROI 止盈，移除止损
    minimal_roi = {
        "0": 0.04,      # 4% 初始止盈 - 大幅提高
        "30": 0.03,     # 30分钟降到 3%
        "60": 0.02,     # 60分钟降到 2%
    }

    # V6 核心：移除固定止损，依赖 SAR 压制
    stoploss = -0.20     # -20% 作为极端保险
    trailing_stop = False

    order_types = {
        'entry': 'market',
        'exit': 'market',
        'stoploss': 'market',
        'stoploss_on_exchange': False,
        'entry_pricing': 'same',
        'exit_pricing': 'same'
    }

    unfilledtimeout = {
        'entry': 10,
        'exit': 10,
        'unit': 'seconds'
    }

    # 杠杆配置
    base_leverage_config = {
        'BTC/USDT:USDT': 2.0,
        'ETH/USDT:USDT': 1.5,
        'SOL/USDT:USDT': 1.5,
        'XRP/USDT:USDT': 1.0,
        'DOGE/USDT:USDT': 1.0
    }

    # 价格缓冲区
    price_buffer_size = 9
    price_buffers = {}

    def informative_pairs(self) -> list:
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        pair = metadata['pair']

        # ========== 核心：SAR 指标 ==========
        df['sar'] = ta.SAR(df['high'].values, df['low'].values,
                          acceleration=0.015, maximum=0.25)

        # SAR 当前位置
        df['above_sar'] = df['close'] > df['sar']

        # SAR 转向检测：从下方突破到上方
        df['sar_reversal_up'] = df['above_sar'] & (df['above_sar'].shift(1) == False)

        # ========== ATR 波动率指标（过滤假突破）==========
        df['atr'] = ta.ATR(df['high'].values, df['low'].values, df['close'].values, timeperiod=14)
        df['atr_ratio'] = df['atr'] / df['close']

        # ========== 辅助：EMA 趋势确认 ==========
        df['ema_9'] = ta.EMA(df['close'].values, timeperiod=9)
        df['ema_21'] = ta.EMA(df['close'].values, timeperiod=21)
        df['ema_trend_up'] = df['ema_9'] > df['ema_21']

        # ========== 辅助：RSI（避免超买）==========
        df['rsi'] = ta.RSI(df['close'].values, timeperiod=14)

        # ========== 核心：9秒动能 ==========
        df['price_9sec_ago'] = df['close'].shift(9)
        df['price_change_9sec'] = (df['close'] - df['price_9sec_ago']) / df['price_9sec_ago']
        df['momentum_9sec_up'] = df['price_change_9sec'] > 0.002  # 提高阈值

        # ========== 成交量确认 ==========
        df['volume_sma'] = ta.SMA(df['volume'].values, timeperiod=20)
        df['volume_ratio'] = df['volume'] / df['volume_sma']

        # ========== 价格缓冲区 ==========
        if pair not in self.price_buffers:
            self.price_buffers[pair] = np.zeros(self.price_buffer_size)

        buffer = self.price_buffers[pair]
        for i in range(len(df)):
            if i >= self.price_buffer_size:
                buffer[:-1] = buffer[1:]
                buffer[-1] = df['close'].iloc[i]

        df['buffer_momentum'] = 0.0
        if len(buffer) >= self.price_buffer_size:
            df['buffer_momentum'] = (buffer[-1] - buffer[0]) / buffer[0]

        return df

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 current_profit: float = 0.0, min_stops: float = 0.0,
                 max_stops: float = 0.0, current_time_rows: DataFrame = None,
                 **kwargs) -> float:
        base_leverage = self.base_leverage_config.get(pair, 1.0)

        # 保守策略
        if current_profit > 0.02:  # 盈利 > 2%
            base_leverage *= 0.5
        elif current_profit < -0.05:  # 亏损 > 5%
            base_leverage *= 0.5

        return min(base_leverage, 2.0)  # 最大杠杆 2x

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        df['enter_long'] = 0

        if len(df) < self.startup_candle_count:
            return df

        # ========== V6 核心：更严格的入场条件 ==========

        entry_conditions = (
            # 1. SAR 转向上（主信号）
            df['sar_reversal_up'] &

            # 2. 9秒动向上（确认）
            df['momentum_9sec_up'] &

            # 3. EMA 趋势向上（辅助）
            df['ema_trend_up'] &

            # 4. RSI 不超买（有空间）
            (df['rsi'] > 35) & (df['rsi'] < 60) &

            # 5. 成交量放大（真突破）
            (df['volume_ratio'] > 1.5) &

            # 6. 缓冲区动量确认
            (df['buffer_momentum'] > 0.0005) &

            # 7. ATR 波动率不过高（过滤极端波动）
            (df['atr_ratio'] < 0.03)
        )

        df.loc[entry_conditions, 'enter_long'] = 1

        return df

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        df['exit'] = 0

        # ========== V6 核心：SAR 压制是主要出场信号 ==========

        exit_conditions = (
            # 1. SAR 压制（趋势反转 - 主信号）
            (df['close'] < df['sar']) |

            # 2. EMA 死叉（趋势反转）
            (df['ema_9'] < df['ema_21']) |

            # 3. RSI 超买（短期顶部）
            (df['rsi'] > 75)
        )

        df.loc[exit_conditions, 'exit'] = 1

        return df

    def custom_exit(self, pair: str, current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs) -> bool:
        # 只作为极端情况保险

        # 紧急止损 - 只有大幅亏损才退出
        if current_profit < -0.20:  # -20% 紧急
            return True

        # 快速止盈
        if current_profit > 0.10:  # 10% 强制止盈
            return True

        return False
