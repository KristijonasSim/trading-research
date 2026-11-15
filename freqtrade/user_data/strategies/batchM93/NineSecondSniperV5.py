from freqtrade.strategy import IStrategy
from pandas import DataFrame
import pandas as pd
import talib.abstract as ta
from datetime import datetime
import numpy as np


class NineSecondSniperV5(IStrategy):
    """
    9秒狙击手策略 V5 - 核心重构版

    回归核心思想：
    1. SAR 转向确认趋势反转（主信号）
    2. 9秒动能确认（辅助确认）
    3. 严格但合理的风控

    V5 修复点：
    - 禁用追踪止损（分钟级震荡太大）
    - 放宽 SAR 参数（更适合分钟级）
    - 简化入场条件（聚焦核心信号）
    - 提高止损容忍度（给趋势发展空间）
    """

    timeframe = '1m'
    max_open_trades = 2
    stake_amount = 100
    startup_candle_count = 100

    # 止盈配置 - 让利润奔跑
    minimal_roi = {
        "0": 0.02,      # 2% 初始止盈
        "15": 0.015,    # 15分钟降到 1.5%
        "30": 0.01,     # 30分钟降到 1%
    }

    # 固定止损 - V5 核心改进：禁用追踪止损
    stoploss = -0.008   # 0.8% 固定止损 - 更宽松
    trailing_stop = False  # 禁用追踪止损（分钟级震荡大，容易被震出）

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

        # ========== 核心：SAR 指标（调整参数更适合分钟级）==========
        # acceleration 降低（反应更慢，避免频繁转向）
        # maximum 提高（允许更大的趋势延续）
        df['sar'] = ta.SAR(df['high'].values, df['low'].values,
                          acceleration=0.015, maximum=0.25)

        # SAR 当前位置：价格在 SAR 上方为多头
        df['above_sar'] = df['close'] > df['sar']

        # SAR 转向检测：从 SAR 下方突破到上方
        df['sar_reversal_up'] = df['above_sar'] & (df['above_sar'].shift(1) == False)

        # ========== 辅助：EMA 趋势确认 ==========
        df['ema_9'] = ta.EMA(df['close'].values, timeperiod=9)
        df['ema_21'] = ta.EMA(df['close'].values, timeperiod=21)
        df['ema_trend_up'] = df['ema_9'] > df['ema_21']

        # ========== 辅助：RSI（避免超买）==========
        df['rsi'] = ta.RSI(df['close'].values, timeperiod=14)

        # ========== 核心：9秒动能 ==========
        # 对比 9 根 K 线的价格变化
        df['price_9sec_ago'] = df['close'].shift(9)
        df['price_change_9sec'] = (df['close'] - df['price_9sec_ago']) / df['price_9sec_ago']
        df['momentum_9sec_up'] = df['price_change_9sec'] > 0

        # ========== 成交量确认（过滤假突破） ==========
        df['volume_sma'] = ta.SMA(df['volume'].values, timeperiod=20)
        df['volume_ratio'] = df['volume'] / df['volume_sma']

        # ========== 价格缓冲区（波动率确认）==========
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
        if current_profit > 0.01:  # 盈利 > 1%
            base_leverage *= 0.5
        elif current_profit < -0.005:  # 亏损 > 0.5%
            base_leverage *= 0.7

        return min(base_leverage, 2.0)  # 最大杠杆 2x

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        df['enter_long'] = 0

        if len(df) < self.startup_candle_count:
            return df

        # ========== V5 核心：简化入场条件 ==========

        entry_conditions = (
            # 1. SAR 转向上（主信号 - 核心思想）
            df['sar_reversal_up'] &

            # 2. 9秒动向上（确认 - 核心思想）
            df['momentum_9sec_up'] &

            # 3. EMA 趋势向上（辅助确认）
            df['ema_trend_up'] &

            # 4. RSI 不超买（有上涨空间）
            (df['rsi'] > 35) & (df['rsi'] < 65) &

            # 5. 成交量放大（真突破）
            (df['volume_ratio'] > 1.2) &

            # 6. 缓冲区动量确认
            (df['buffer_momentum'] > 0)
        )

        df.loc[entry_conditions, 'enter_long'] = 1

        return df

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        df['exit'] = 0

        # ========== V5 核心：简化出场条件 ==========
        # 让 ROI 和止损处理，只处理明确的反转信号

        exit_conditions = (
            # 1. SAR 压制（趋势明确反转）
            (df['close'] < df['sar']) |

            # 2. EMA 死叉（趋势反转）
            (df['ema_9'] < df['ema_21']) |

            # 3. 9秒动量向下（动能消失）
            (df['price_change_9sec'] < -0.002)
        )

        df.loc[exit_conditions, 'exit'] = 1

        return df

    def custom_exit(self, pair: str, current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs) -> bool:
        # 只作为最后的保险

        # 紧急止损
        if current_profit < -0.015:  # -1.5% 紧急止损
            return True

        return False
