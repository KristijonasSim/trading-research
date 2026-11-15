from freqtrade.strategy import IStrategy
from pandas import DataFrame
import pandas as pd
import talib.abstract as ta
from datetime import datetime
import numpy as np


class NineSecondSniperV2(IStrategy):
    """
    9秒狙击手策略 V2 - 激进智能版

    核心逻辑：
    - SAR + ADX 组合确认趋势强度
    - ATR 波动率过滤市场状态
    - 动态杠杆根据趋势强度调整
    - 支持做空逻辑（熊市对冲）
    """

    timeframe = '1m'
    max_open_trades = 3
    stake_amount = 100
    startup_candle_count = 100

    minimal_roi = {
        "0": 0.02,     # 2% 止盈 - 让利润奔跑
        "30": 0.015,    # 30分钟降到1.5%
        "60": 0.01,     # 60分钟降到1%
    }

    stoploss = -0.008  # 0.8% 紧凑止损
    trailing_stop = True  # 启用追踪止损
    trailing_stop_positive = 0.005  # 0.5% 盈利后启动
    trailing_stop_positive_offset = 0.008  # 0.8% 偏离

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

    # 基础杠杆配置
    base_leverage_config = {
        'BTC/USDT:USDT': 5.0,
        'ETH/USDT:USDT': 4.0,
        'SOL/USDT:USDT': 3.0,
        'XRP/USDT:USDT': 3.0,
        'DOGE/USDT:USDT': 2.0
    }

    # 价格缓冲区
    price_buffer_size = 9
    price_buffers = {}

    # 做空交易状态
    short_positions = {}

    def informative_pairs(self) -> list:
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        pair = metadata['pair']

        # ========== 核心指标 ==========

        # SAR 指标 - 找趋势反转点
        df['sar'] = ta.SAR(df['high'].values, df['low'].values,
                          acceleration=0.02, maximum=0.2)

        # ADX - 趋势强度指标
        df['adx'] = ta.ADX(df['high'].values, df['low'].values, df['close'].values, timeperiod=14)

        # ATR - 波动率
        df['atr'] = ta.ATR(df['high'].values, df['low'].values, df['close'].values, timeperiod=14)
        df['atr_pct'] = df['atr'] / df['close']  # ATR 百分比

        # EMA 趋势确认
        df['ema_9'] = ta.EMA(df['close'].values, timeperiod=9)
        df['ema_21'] = ta.EMA(df['close'].values, timeperiod=21)

        # RSI 避免超买超卖
        df['rsi'] = ta.RSI(df['close'].values, timeperiod=14)

        # MACD 动能确认
        macd, macdsignal, macdhist = ta.MACD(df['close'].values)
        df['macd'] = macd
        df['macd_signal'] = macdsignal
        df['macd_hist'] = macdhist

        # 成交量
        df['volume_sma'] = ta.SMA(df['volume'].values, timeperiod=20)
        df['volume_ratio'] = df['volume'] / df['volume_sma']

        # ========== 9秒动能 ==========

        # 当前价格 vs 9根K线前
        df['price_9sec_ago'] = df['close'].shift(9)
        df['price_change_9sec'] = (df['close'] - df['price_9sec_ago']) / df['price_9sec_ago']
        df['volatility_9sec'] = abs(df['price_change_9sec'])

        # ========== 价格缓冲区维护 ==========
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

        # ========== 市场状态判断 ==========

        # 多头趋势
        df['trend_up'] = (
            (df['ema_9'] > df['ema_21']) &  # EMA 金叉
            (df['macd'] > df['macd_signal']) &  # MACD 金叉
            (df['close'] > df['sar'])  # SAR 支撑
        )

        # 空头趋势
        df['trend_down'] = (
            (df['ema_9'] < df['ema_21']) &
            (df['macd'] < df['macd_signal']) &
            (df['close'] < df['sar'])
        )

        # 强趋势判断 (ADX > 25 表示有明确趋势)
        df['strong_trend'] = df['adx'] > 25

        # 高波动市场
        df['high_volatility'] = df['atr_pct'] > 0.02  # ATR > 2%

        return df

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 current_profit: float = 0.0, min_stops: float = 0.0,
                 max_stops: float = 0.0, current_time_rows: DataFrame = None,
                 **kwargs) -> float:
        base_leverage = self.base_leverage_config.get(pair, 3.0)

        # 根据趋势强度动态调整杠杆
        if current_time_rows is not None and not current_time_rows.empty:
            adx = current_time_rows['adx'].iloc[-1] if 'adx' in current_time_rows.columns else 20
            rsi = current_time_rows['rsi'].iloc[-1] if 'rsi' in current_time_rows.columns else 50

            # 强趋势 + 中位 RSI = 更高杠杆
            if adx > 35 and 40 < rsi < 60:
                base_leverage *= 1.3
            # 弱趋势或极端 RSI = 降低杠杆
            elif adx < 20 or rsi > 75 or rsi < 25:
                base_leverage *= 0.6

        # 盈利时动态调整
        if current_profit > 0.01:  # 盈利 > 1%
            base_leverage *= 0.7  # 降低杠杆保护利润
        elif current_profit < -0.005:  # 亏损 > 0.5%
            base_leverage *= 0.8  # 降低杠杆控制风险

        # 限制最大杠杆
        return min(base_leverage, 10.0)

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        df['enter_long'] = 0
        df['enter_short'] = 0

        if len(df) < self.startup_candle_count:
            return df

        # ========== 做多条件 ==========
        long_conditions = (
            # 趋势确认
            df['trend_up'] &                    # 上涨趋势
            df['strong_trend'] &                  # 强趋势 (ADX > 25)
            # RSI 过滤（避免超买）
            (df['rsi'] > 35) & (df['rsi'] < 70) &  # 中位区
            # 成交量确认
            (df['volume_ratio'] > 1.3) &          # 量能放大
            # 动能确认
            (df['price_change_9sec'] > 0.001) &   # 向上动
            (df['buffer_momentum'] > 0.0005) &       # 缓冲区动
            # 波动率过滤
            (df['atr_pct'] < 0.03)                # 波动率适中
        )

        # ========== 做空条件 ==========
        short_conditions = (
            df['trend_down'] &                   # 下跌趋势
            df['strong_trend'] &                 # 强趋势
            (df['rsi'] < 65) & (df['rsi'] > 30) &  # RSI 区
            (df['volume_ratio'] > 1.3) &          # 量能确认
            (df['price_change_9sec'] < -0.001) &  # 向下动
            (df['buffer_momentum'] < -0.0005) &    # 缓冲区动
            (df['atr_pct'] < 0.03)               # 波动率适中
        )

        df.loc[long_conditions, 'enter_long'] = 1
        df.loc[short_conditions, 'enter_short'] = 1

        return df

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        df['exit_long'] = 0
        df['exit_short'] = 0

        # 多单退出
        long_exit = (
            (df['ema_9'] < df['ema_21']) |      # 趋势反转
            (df['rsi'] > 75) |                      # 超买
            (df['macd'] < df['macd_signal']) |   # MACD 死叉
            (df['adx'] < 15)                       # 趋势减弱
        )

        # 空单退出
        short_exit = (
            (df['ema_9'] > df['ema_21']) |
            (df['rsi'] < 25) |                      # 超卖
            (df['macd'] > df['macd_signal']) |   # MACD 金叉
            (df['adx'] < 15)
        )

        df.loc[long_exit, 'exit_long'] = 1
        df.loc[short_exit, 'exit_short'] = 1

        return df

    def custom_exit(self, pair: str, current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs) -> bool:
        # 紧凑止损 - 防止亏损扩大
        if current_profit < -0.012:  # -1.2% 止损
            return True

        # 止盈 - 追踪止盈主要处理，这里作为保险
        if current_profit > 0.05:  # 5% 强制止盈
            return True

        return False
