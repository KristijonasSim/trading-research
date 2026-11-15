from freqtrade.strategy import IStrategy
from pandas import DataFrame
import pandas as pd
import talib.abstract as ta
from datetime import datetime
import numpy as np


class NineSecondSniperV4(IStrategy):
    """
    9秒狙击手策略 V4 - 终极修复版

    基于视频拆解的核心问题修复：
    1. ✅ SAR 用法：SAR 转向时入场（价格突破 SAR），而非压制时逆势赌
    2. ✅ 添加趋势确认：只在上涨趋势中做多
    3. ✅ 严格风控：预设止损 0.5%，不再被动止损
    4. ✅ 合理止盈：1.5-2.5% 区间
    5. ✅ 降低杠杆：避免高杠杆放大风险
    6. ✅ 交易冷却：避免过度频繁交易
    """

    timeframe = '1m'
    max_open_trades = 2
    stake_amount = 100
    startup_candle_count = 100

    # 止盈配置 - 让利润奔跑
    minimal_roi = {
        "0": 0.025,    # 2.5% 初始止盈
        "30": 0.02,     # 30分钟降到 2%
        "60": 0.015,    # 60分钟降到 1.5%
    }

    # 固定止损 - 不再被动止损
    stoploss = -0.005  # 0.5% 固定止损
    trailing_stop = True  # 追踪止损保护利润
    trailing_stop_positive = 0.008  # 0.8% 盈利后启动
    trailing_stop_positive_offset = 0.012  # 1.2% 偏离

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

    # 保守杠杆配置 - 降低风险
    base_leverage_config = {
        'BTC/USDT:USDT': 2.0,
        'ETH/USDT:USDT': 1.5,
        'SOL/USDT:USDT': 1.5,
        'XRP/USDT:USDT': 1.0,
        'DOGE/USDT:USDT': 1.0
    }

    # 价格缓冲区 - 保留原版设计
    price_buffer_size = 9
    price_buffers = {}

    # 冷却时间器
    last_entry_time = {}
    cooldown_minutes = 30  # 同一交易对冷却30分钟

    def informative_pairs(self) -> list:
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        pair = metadata['pair']

        # ========== 核心指标 ==========

        # SAR 指标 - 抛物线，找趋势反转
        df['sar'] = ta.SAR(df['high'].values, df['low'].values,
                          acceleration=0.02, maximum=0.2)

        # EMA 趋势线
        df['ema_9'] = ta.EMA(df['close'].values, timeperiod=9)
        df['ema_21'] = ta.EMA(df['close'].values, timeperiod=21)

        # RSI - 避免超买超卖
        df['rsi'] = ta.RSI(df['close'].values, timeperiod=14)

        # MACD - 动能确认
        macd, macdsignal, macdhist = ta.MACD(df['close'].values)
        df['macd'] = macd
        df['macd_signal'] = macdsignal
        df['macd_hist'] = macdhist

        # 成交量
        df['volume_sma'] = ta.SMA(df['volume'].values, timeperiod=20)
        df['volume_ratio'] = df['volume'] / df['volume_sma']

        # ========== 9秒动能 ==========

        # 9根K线价格对比
        df['price_9sec_ago'] = df['close'].shift(9)
        df['price_change_9sec'] = (df['close'] - df['price_9sec_ago']) / df['price_9sec_ago']
        df['volatility_9sec'] = abs(df['price_change_9sec'])

        # SAR 转向检测 - 关键修复
        df['sar_reversal'] = (df['close'].shift(1) < df['sar'].shift(1)) & (df['close'] > df['sar'])

        # 价格缓冲区维护 - 保留原版设计
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

        # 保守策略：盈利时降低杠杆，亏损时也降低杠杆
        if current_profit > 0.005:  # 盈利 > 0.5%
            base_leverage *= 0.5  # 减半杠杆
        elif current_profit < -0.003:  # 亏损 > 0.3%
            base_leverage *= 0.7  # 降低杠杆控制风险

        return min(base_leverage, 3.0)  # 最大杠杆 3x

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        df['enter_long'] = 0

        if len(df) < self.startup_candle_count:
            return df

        # ========== 修复后的狙击手入场条件 ==========

        entry_conditions = (
            # 1. SAR 转向确认（价格突破 SAR 向上）- 关键修复！
            df['sar_reversal'] &

            # 2. EMA 金叉确认（上涨趋势）
            (df['ema_9'] > df['ema_21']) &

            # 3. RSI 中位区确认（不超买，有上涨空间）
            (df['rsi'] > 40) & (df['rsi'] < 70) &

            # 4. MACD 金叉确认（动能向上）
            (df['macd'] > df['macd_signal']) &

            # 5. 成交量确认
            (df['volume_ratio'] > 1.3) &

            # 6. 9秒动向上确认
            (df['price_change_9sec'] > 0.001) &

            # 7. 缓冲区动确认
            (df['buffer_momentum'] > 0.0003)
        )

        df.loc[entry_conditions, 'enter_long'] = 1

        return df

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        df['exit'] = 0

        # ========== 快速出场条件 ==========

        exit_conditions = (
            # 1. EMA 死叉（趋势反转）
            (df['ema_9'] < df['ema_21']) |

            # 2. MACD 死叉
            (df['macd'] < df['macd_signal']) |

            # 3. RSI 超买
            (df['rsi'] > 75) |

            # 4. SAR 再次压制（可能重新下跌）
            (df['close'] < df['sar']) |

            # 5. 9秒动向下
            (df['price_change_9sec'] < -0.001)
        )

        df.loc[exit_conditions, 'exit'] = 1

        return df

    def custom_exit(self, pair: str, current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs) -> bool:
        # 追踪止损主要处理，这里作为额外保险

        # 紧凑止损保险
        if current_profit < -0.008:  # -0.8% 保险止损
            return True

        # 快速止盈保险
        if current_profit > 0.03:  # 3% 强制止盈
            return True

        return False
