# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
# --- Do not remove these libs ---
import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from typing import Optional, Union

from freqtrade.strategy import (
    IStrategy,
    merge_informative_pair,
    stoploss_from_open,
    IntParameter,
    DecimalParameter,
    CategoricalParameter,
)
from freqtrade.strategy import timeframe_to_prev_date
from freqtrade.persistence import Trade
from freqtrade.exchange import timeframe_to_minutes
from functools import reduce

import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib


class Rule123And2BStrategy(IStrategy):
    """
    123法则 & 2B法则策略 (维克多·斯波朗迪欧)

    123法则:
    1. 趋势线被突破
    2. 破高/破低失败 (形成更低的高点或更高的低点)
    3. 跌破前期低点或突破前期高点

    2B法则:
    1. 创出新高/新低
    2. 快速回落/反弹并跌破/突破前高/前低
    """

    # Strategy interface version - allow new iterations of the strategy interface.
    # Check the documentation or the Sample strategy to get the latest version.
    INTERFACE_VERSION = 3

    # Optimal timeframe for the strategy.
    timeframe = "5m"

    # Can this strategy go short?
    can_short: bool = True

    # Minimal ROI designed for the strategy.
    minimal_roi = {"0": 0.015, "30": 0.01, "60": 0.005, "120": 0}

    # Optimal stoploss designed for the strategy.
    stoploss = -0.015

    # Trailing stoploss
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.015
    trailing_only_offset_is_reached = True

    # Run "populate_indicators" only for new candle.
    process_only_new_candles = True

    # These values can be overridden in the config.
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # Number of candles the strategy requires before producing valid signals
    startup_candle_count: int = 50

    # Strategy parameters
    lookback_len = IntParameter(8, 15, default=12, space="buy", optimize=True)
    use_atr_filter = CategoricalParameter([True, False], default=True, space="buy", optimize=True)
    atr_len = IntParameter(14, 21, default=14, space="buy", optimize=True)
    atr_mult = DecimalParameter(0.15, 0.4, default=0.2, space="buy", optimize=True)
    use_123_rule = CategoricalParameter([True, False], default=True, space="buy", optimize=True)
    use_2b_rule = CategoricalParameter([True, False], default=True, space="buy", optimize=True)

    # 添加额外的过滤参数
    volume_filter = CategoricalParameter([True, False], default=True, space="buy", optimize=True)
    volume_multiplier = DecimalParameter(1.2, 2.5, default=1.5, space="buy", optimize=True)
    rsi_filter = CategoricalParameter([True, False], default=True, space="buy", optimize=True)
    rsi_oversold = IntParameter(20, 35, default=30, space="buy", optimize=True)
    rsi_overbought = IntParameter(65, 80, default=70, space="buy", optimize=True)

    def leverage(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_leverage: float,
        max_leverage: float,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> float:
        """
        自定义杠杆倍数
        """
        return min(proposed_leverage, 10.0)  # 最大10倍杠杆

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        添加技术指标到数据框
        """
        # ATR指标
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=self.atr_len.value)

        # RSI指标
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        # 成交量指标
        dataframe["volume_sma"] = ta.SMA(dataframe["volume"], timeperiod=20)

        # 计算枢轴点 (Pivot Points)
        # 使用rolling window来寻找局部高低点
        lookback = self.lookback_len.value

        # 计算局部最高点和最低点
        dataframe["pivot_high"] = (
            dataframe["high"].rolling(window=lookback * 2 + 1, center=True).max()
        )
        dataframe["pivot_low"] = (
            dataframe["low"].rolling(window=lookback * 2 + 1, center=True).min()
        )

        # 标记真正的枢轴点 (当前值等于rolling max/min时)
        dataframe["is_pivot_high"] = (dataframe["high"] == dataframe["pivot_high"]).shift(lookback)
        dataframe["is_pivot_low"] = (dataframe["low"] == dataframe["pivot_low"]).shift(lookback)

        # 获取最近的枢轴点值
        dataframe["ph1"] = np.nan  # 最近的枢轴高点
        dataframe["ph2"] = np.nan  # 次近的枢轴高点
        dataframe["pl1"] = np.nan  # 最近的枢轴低点
        dataframe["pl2"] = np.nan  # 次近的枢轴低点

        # 向前填充枢轴点值
        ph1, ph2, pl1, pl2 = np.nan, np.nan, np.nan, np.nan

        for i in range(len(dataframe)):
            if dataframe.iloc[i]["is_pivot_high"]:
                ph2 = ph1
                ph1 = dataframe.iloc[i]["high"]
            if dataframe.iloc[i]["is_pivot_low"]:
                pl2 = pl1
                pl1 = dataframe.iloc[i]["low"]

            dataframe.iloc[i, dataframe.columns.get_loc("ph1")] = ph1
            dataframe.iloc[i, dataframe.columns.get_loc("ph2")] = ph2
            dataframe.iloc[i, dataframe.columns.get_loc("pl1")] = pl1
            dataframe.iloc[i, dataframe.columns.get_loc("pl2")] = pl2

        # ATR过滤器
        dataframe["atr_filter"] = np.where(
            self.use_atr_filter.value, dataframe["atr"] * self.atr_mult.value, 0
        )

        # 成交量过滤器
        dataframe["volume_filter_ok"] = np.where(
            self.volume_filter.value,
            dataframe["volume"] > (dataframe["volume_sma"] * self.volume_multiplier.value),
            True,
        )

        # RSI过滤条件
        dataframe["rsi_long_ok"] = np.where(
            self.rsi_filter.value, dataframe["rsi"] < self.rsi_oversold.value, True
        )

        dataframe["rsi_short_ok"] = np.where(
            self.rsi_filter.value, dataframe["rsi"] > self.rsi_overbought.value, True
        )

        # 123法则信号
        # 做空信号: 更低的高点 + 跌破前期低点
        dataframe["rule_123_step2_short"] = (
            (~dataframe["ph1"].isna())
            & (~dataframe["ph2"].isna())
            & (dataframe["ph1"] > dataframe["ph2"])
        )

        dataframe["rule_123_step3_short"] = (
            (~dataframe["pl1"].isna())
            & (dataframe["low"] < (dataframe["pl1"] - dataframe["atr_filter"]))
            & dataframe["rule_123_step2_short"]
            & dataframe["volume_filter_ok"]
            & dataframe["rsi_short_ok"]
        )

        # 做多信号: 更高的低点 + 突破前期高点
        dataframe["rule_123_step2_long"] = (
            (~dataframe["pl1"].isna())
            & (~dataframe["pl2"].isna())
            & (dataframe["pl1"] < dataframe["pl2"])
        )

        dataframe["rule_123_step3_long"] = (
            (~dataframe["ph1"].isna())
            & (dataframe["high"] > (dataframe["ph1"] + dataframe["atr_filter"]))
            & dataframe["rule_123_step2_long"]
            & dataframe["volume_filter_ok"]
            & dataframe["rsi_long_ok"]
        )

        # 2B法则信号
        # 做空信号: 创新高后快速回落
        dataframe["rule_2b_short"] = (
            (~dataframe["ph1"].isna())
            & (dataframe["high"] > (dataframe["ph1"] + dataframe["atr_filter"]))
            & (dataframe["close"] < (dataframe["ph1"] - dataframe["atr_filter"]))
            & dataframe["volume_filter_ok"]
            & dataframe["rsi_short_ok"]
        )

        # 做多信号: 创新低后快速反弹
        dataframe["rule_2b_long"] = (
            (~dataframe["pl1"].isna())
            & (dataframe["low"] < (dataframe["pl1"] - dataframe["atr_filter"]))
            & (dataframe["close"] > (dataframe["pl1"] + dataframe["atr_filter"]))
            & dataframe["volume_filter_ok"]
            & dataframe["rsi_long_ok"]
        )

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        基于TA指标填充买入信号
        """
        conditions_long = []
        conditions_short = []

        # 123法则做多条件
        if self.use_123_rule.value:
            conditions_long.append(dataframe["rule_123_step3_long"])
            conditions_short.append(dataframe["rule_123_step3_short"])

        # 2B法则条件
        if self.use_2b_rule.value:
            conditions_long.append(dataframe["rule_2b_long"])
            conditions_short.append(dataframe["rule_2b_short"])

        # 合并条件
        if conditions_long:
            dataframe.loc[reduce(lambda x, y: x | y, conditions_long), "enter_long"] = 1

        if conditions_short:
            dataframe.loc[reduce(lambda x, y: x | y, conditions_short), "enter_short"] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        基于TA指标填充卖出信号
        """
        # 反向信号平仓
        conditions_exit_long = []
        conditions_exit_short = []

        # 当出现做空信号时平多仓
        if self.use_123_rule.value:
            conditions_exit_long.append(dataframe["rule_123_step3_short"])
            conditions_exit_short.append(dataframe["rule_123_step3_long"])

        if self.use_2b_rule.value:
            conditions_exit_long.append(dataframe["rule_2b_short"])
            conditions_exit_short.append(dataframe["rule_2b_long"])

        # 合并退出条件
        if conditions_exit_long:
            dataframe.loc[reduce(lambda x, y: x | y, conditions_exit_long), "exit_long"] = 1

        if conditions_exit_short:
            dataframe.loc[reduce(lambda x, y: x | y, conditions_exit_short), "exit_short"] = 1

        return dataframe

    def custom_stoploss(
        self,
        pair: str,
        trade: "Trade",
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        after_fill: bool,
        **kwargs,
    ) -> float | None:
        """
        自定义止损逻辑
        """
        # 使用ATR动态止损
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()

        if "atr" in last_candle:
            atr_stop_distance = last_candle["atr"] * 2.0

            if trade.is_short:
                # 做空时, 止损在入场价格之上
                stop_price = trade.open_rate + atr_stop_distance
                return (stop_price - current_rate) / current_rate
            else:
                # 做多时, 止损在入场价格之下
                stop_price = trade.open_rate - atr_stop_distance
                return (stop_price - current_rate) / current_rate

        return self.stoploss

    def custom_exit(
        self,
        pair: str,
        trade: "Trade",
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs,
    ) -> str | bool | None:
        """
        自定义退出逻辑
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        dataframe.iloc[-1].squeeze()

        # 快速止盈逻辑
        if current_profit > 0.03:  # 3%以上利润时考虑退出
            return "quick_profit"

        return None
