from freqtrade.strategy import IStrategy
from pandas import DataFrame
import pandas as pd
import talib.abstract as ta
from datetime import datetime
import numpy as np


class NineSecondSniperV9(IStrategy):
    """
    9秒狙击手策略 V9 - 平衡版

    V9 思路：
    1. 保持高交易频率（符合 9 秒狙击手思想）
    2. 移除固定止损（完全依赖 SAR）
    3. 调整入场条件，提高信号质量
    """

    timeframe = '1m'
    max_open_trades = 2
    stake_amount = 100
    startup_candle_count = 100

    # 止盈配置
    minimal_roi = {
        "0": 0.025,     # 2.5% 初始止盈
        "20": 0.02,      # 20分钟降到 2%
        "40": 0.015,     # 40分钟降到 1.5%
    }

    # V9 核心：无固定止损，完全依赖 SAR
    stoploss = -0.30     # -30% 极端保险
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
        'ETH/USDT:USDT': 2.0,
        'SOL/USDT:USDT': 1.5,
        'XRP/USDT:USDT': 1.0,
        'DOGE/USDT:USDT': 1.0
    }

    def informative_pairs(self) -> list:
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()

        # ========== 核心：SAR 指标 ==========
        df['sar'] = ta.SAR(df['high'].values, df['low'].values,
                          acceleration=0.02, maximum=0.2)

        # SAR 当前位置
        df['above_sar'] = df['close'] > df['sar']

        # SAR 转向检测：从下方突破到上方
        df['sar_reversal_up'] = df['above_sar'] & (df['above_sar'].shift(1) == False)

        # ========== 核心：9秒动能 ==========
        df['price_9sec_ago'] = df['close'].shift(9)
        df['price_change_9sec'] = (df['close'] - df['price_9sec_ago']) / df['price_9sec_ago']
        df['momentum_9sec_up'] = df['price_change_9sec'] > 0.0005

        # ========== 辅助：EMA 趋势 ==========
        df['ema_9'] = ta.EMA(df['close'].values, timeperiod=9)
        df['ema_21'] = ta.EMA(df['close'].values, timeperiod=21)
        df['ema_trend_up'] = df['ema_9'] > df['ema_21']

        # ========== 辅助：RSI ==========
        df['rsi'] = ta.RSI(df['close'].values, timeperiod=14)

        # ========== 辅助：成交量和 ATR ==========
        df['volume_sma'] = ta.SMA(df['volume'].values, timeperiod=20)
        df['volume_ratio'] = df['volume'] / df['volume_sma']

        df['atr'] = ta.ATR(df['high'].values, df['low'].values, df['close'].values, timeperiod=14)
        df['atr_ratio'] = df['atr'] / df['close']

        return df

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 current_profit: float = 0.0, min_stops: float = 0.0,
                 max_stops: float = 0.0, current_time_rows: DataFrame = None,
                 **kwargs) -> float:
        base_leverage = self.base_leverage_config.get(pair, 1.0)

        if current_profit > 0.02:
            base_leverage *= 0.5
        elif current_profit < -0.05:
            base_leverage *= 0.5

        return min(base_leverage, 2.0)

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        df['enter_long'] = 0

        if len(df) < self.startup_candle_count:
            return df

        # ========== V9：平衡入场条件 ==========

        entry_conditions = (
            # 1. SAR 转向上（主信号）
            df['sar_reversal_up'] &

            # 2. 9秒动向上（确认）
            df['momentum_9sec_up'] &

            # 3. EMA 趋势向上（辅助）
            df['ema_trend_up'] &

            # 4. RSI 避免极端（30-70）
            (df['rsi'] > 30) & (df['rsi'] < 70) &

            # 5. 成交量（1.1x）
            (df['volume_ratio'] > 1.1) &

            # 6. ATR 波动率过滤（< 0.04）
            (df['atr_ratio'] < 0.04)
        )

        df.loc[entry_conditions, 'enter_long'] = 1

        return df

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        df['exit'] = 0

        # ========== V9：SAR 主导出场 ==========

        exit_conditions = (
            # 1. SAR 压制（趋势反转 - 主信号）
            (df['close'] < df['sar']) |

            # 2. EMA 死叉（趋势反转）
            (df['ema_9'] < df['ema_21']) |

            # 3. RSI 超买（> 75）
            (df['rsi'] > 75) |

            # 4. 9秒动量向下（< -0.002）
            (df['price_change_9sec'] < -0.002)
        )

        df.loc[exit_conditions, 'exit'] = 1

        return df

    def custom_exit(self, pair: str, current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs) -> bool:
        # 极端保险
        if current_profit < -0.20:  # -20% 紧急
            return True

        return False
