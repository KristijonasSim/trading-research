from typing import Dict, List

import numpy as np
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy.interface import IStrategy


class TrendBreakout(IStrategy):
    """
    一个偏激进的趋势突破策略示例（1 分钟级别）

    设计目标：
    - 使用 1m K 线，让机器人“动起来”，多一些信号。
    - 只依赖 OHLCV 和常见技术指标（EMA、RSI、布林带、成交量），
      不依赖订单簿和 websocket，尽量适配你现在网络环境。
    - 顺势 + 突破：价格在大趋势均线上方、短均线多头排列，突破近期高点且放量时做多。
    - 快速止盈 + 紧止损：默认 1% 止盈，3% 止损（dry-run 下看效果，实盘前务必回测！）
    """

    # 使用 1 分钟周期
    timeframe: str = "1m"

    # 允许多空（注意：实盘空头需要期货/保证金支持）
    can_short: bool = True

    # 更激进：给价格更多波动空间，同时更快止盈
    # 最大亏损改为 -5%，默认止盈改为 0.3%
    stoploss: float = -0.05

    minimal_roi: Dict[str, float] = {
        "0": 0.003
    }

    # 只在新 K 线来临时计算信号，减少频繁重复计算
    process_only_new_candles: bool = True

    # 启动时最少需要多少根 K 线（用来计算均线等）
    startup_candle_count: int = 60

    # 用于计算近期高点/低点的窗口，越小越“敏感”，信号越多
    breakout_window: int = 20

    use_custom_stoploss: bool = False

    def informative_pairs(self) -> List:
        """
        当前策略不使用额外的 informative pairs（如更大周期 / 其他交易对）。
        先保持简单，后面如果要做套利 / 配对再扩展。
        """
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        计算本策略需要用到的各类技术指标
        """
        if dataframe.empty:
            return dataframe

        # EMA 趋势线：快速 / 慢速 / 长期趋势
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=9)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema_trend"] = ta.EMA(dataframe, timeperiod=200)

        # RSI
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        # 布林带
        close_series = dataframe["close"].astype("float64")

        bb_upper, bb_middle, bb_lower = ta.BBANDS(
            close_series,
            timeperiod=20,
            nbdevup=2.0,
            nbdevdn=2.0,
            matype=0,
        )

        # 将返回的 numpy 数组转换为带索引的 Series，方便后续使用 replace 等方法
        dataframe["bb_upperband"] = pd.Series(bb_upper, index=dataframe.index)
        dataframe["bb_middleband"] = pd.Series(bb_middle, index=dataframe.index)
        dataframe["bb_lowerband"] = pd.Series(bb_lower, index=dataframe.index)

        # 布林带百分位（0 ~ 1，0 在下轨附近，1 在上轨附近）
        band_width = dataframe["bb_upperband"] - dataframe["bb_lowerband"]
        band_width.replace(0, np.nan, inplace=True)
        dataframe["bb_percent"] = (dataframe["close"] - dataframe["bb_lowerband"]) / band_width

        # 成交量均线，用来判断是否“放量”
        dataframe["vol_ma_fast"] = dataframe["volume"].rolling(20).mean()
        dataframe["vol_ma_slow"] = dataframe["volume"].rolling(50).mean()

        # 近期高点/低点，用于突破判断。使用较小的窗口让策略更敏感。
        window = getattr(self, "breakout_window", 20)
        dataframe["recent_high"] = dataframe["high"].rolling(window).max()
        dataframe["recent_low"] = dataframe["low"].rolling(window).min()

        # 处理缺失值，避免在条件判断时出现 NaN
        dataframe.fillna(method="ffill", inplace=True)
        dataframe.fillna(method="bfill", inplace=True)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        进场逻辑（多空双向的顺势突破）：

        多头条件大致为：
        1. 大趋势向上：收盘价在 ema_trend 上方。
        2. 多头排列：ema_fast > ema_slow。
        3. 向上突破：当前收盘价高于最近 30 根 K 线的最高价（recent_high 的前一根）。
        4. RSI 在 50~80 中间位置。
        5. 放量：当前成交量 > 慢速成交量均线的 1.2 倍。

        空头条件大致为：
        1. 大趋势向下：收盘价在 ema_trend 下方。
        2. 空头排列：ema_fast < ema_slow。
        3. 向下突破：当前收盘价低于最近 30 根 K 线的最低价（recent_low 的前一根）。
        4. RSI 在 20~50 区间（不过度超卖）。
        5. 放量：当前成交量 > 慢速成交量均线的 1.2 倍。
        """
        if dataframe.empty:
            return dataframe

        # 默认先清零
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0

        # ------- 多头逻辑 -------
        long_conditions = []

        # 1. 趋势向上：价格在中期均线之上（比 ema_trend 更宽松）
        long_conditions.append(dataframe["close"] > dataframe["ema_slow"])

        # 2. 短均线多头排列
        long_conditions.append(dataframe["ema_fast"] > dataframe["ema_slow"])

        # 3. 突破最近高点（使用 recent_high 的前一根，避免未来函数）
        long_conditions.append(dataframe["close"] > dataframe["recent_high"].shift(1))

        # 4. RSI 在相对健康的上升区间（稍微放宽一点）
        long_conditions.append(dataframe["rsi"] > 45)
        long_conditions.append(dataframe["rsi"] < 80)

        # 5. 放量条件放宽：只要略高于短期均量即可
        long_conditions.append(
            dataframe["volume"] > (dataframe["vol_ma_fast"] * 1.05)
        )

        # 6. 确保没有缺失值，且 volume > 0
        long_conditions.append(dataframe["volume"] > 0)

        if long_conditions:
            dataframe.loc[
                np.logical_and.reduce(long_conditions),
                "enter_long",
            ] = 1

        # ------- 空头逻辑 -------
        short_conditions = []

        # 1. 趋势向下：价格在中期均线之下
        short_conditions.append(dataframe["close"] < dataframe["ema_slow"])

        # 2. 短均线空头排列
        short_conditions.append(dataframe["ema_fast"] < dataframe["ema_slow"])

        # 3. 向下突破最近低点（使用 recent_low 的前一根，避免未来函数）
        short_conditions.append(dataframe["close"] < dataframe["recent_low"].shift(1))

        # 4. RSI 在 25~55 区间（略微放宽，让空头信号更多一些）
        short_conditions.append(dataframe["rsi"] < 55)
        short_conditions.append(dataframe["rsi"] > 25)

        # 5. 放量条件放宽：略高于短期均量即可
        short_conditions.append(
            dataframe["volume"] > (dataframe["vol_ma_fast"] * 1.05)
        )

        # 6. 基本防守：volume > 0
        short_conditions.append(dataframe["volume"] > 0)

        if short_conditions:
            dataframe.loc[
                np.logical_and.reduce(short_conditions),
                "enter_short",
            ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        出场逻辑（多空双向，稍微“钝化”一点）：

        思路：
        - 不再因为单一条件非常容易就触发 exit_signal；
        - 多头：只有在“明显转弱” 或 “极度过热” 时才离场；
        - 空头：只有在“明显反弹” 或 “极度超跌” 时才离场；
        - 其余情况交给 minimal_roi / stoploss 或你手动平仓。
        """
        if dataframe.empty:
            return dataframe

        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0

        # ------- 多头离场 -------
        # 条件 1：价格跌回快均线下方，且 RSI 明显走弱（< 40）
        long_weak = (dataframe["rsi"] < 40) & (dataframe["close"] < dataframe["ema_fast"])

        # 条件 2：价格极度过热，接近布林带上轨（> 97% 分位）
        long_overbought = dataframe["bb_percent"] > 0.97

        dataframe.loc[long_weak | long_overbought, "exit_long"] = 1

        # ------- 空头离场 -------
        # 条件 1：价格重新站上快均线，且 RSI 明显走强（> 60），认为反弹动能较强
        short_rebound = (dataframe["rsi"] > 60) & (dataframe["close"] > dataframe["ema_fast"])

        # 条件 2：价格极度超跌，接近布林带下轨（< 3% 分位）
        short_oversold = dataframe["bb_percent"] < 0.03

        dataframe.loc[short_rebound | short_oversold, "exit_short"] = 1

        return dataframe