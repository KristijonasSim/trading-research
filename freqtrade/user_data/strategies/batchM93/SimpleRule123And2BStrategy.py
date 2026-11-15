# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
# --- Do not remove these libs ---
import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from typing import Optional, Union
from functools import reduce

from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter, CategoricalParameter
from freqtrade.persistence import Trade

import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib


class SimpleRule123And2BStrategy(IStrategy):
    """
    简化版123法则 & 2B法则策略
    专注于核心信号, 减少过度优化
    """

    INTERFACE_VERSION = 3
    timeframe = "5m"
    can_short: bool = True

    # 简化的ROI和止损设置
    minimal_roi = {"0": 0.02, "60": 0.01, "120": 0}

    stoploss = -0.02
    trailing_stop = False  # 简化, 不使用追踪止损

    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    startup_candle_count: int = 30

    # 简化的参数设置
    lookback_len = IntParameter(8, 15, default=10, space="buy", optimize=True)
    atr_len = IntParameter(14, 21, default=14, space="buy", optimize=True)
    atr_mult = DecimalParameter(0.1, 0.3, default=0.15, space="buy", optimize=True)

    # 最小价格变动阈值(避免微小波动)
    min_price_change = DecimalParameter(0.005, 0.02, default=0.01, space="buy", optimize=True)

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
        return min(proposed_leverage, 5.0)  # 降低杠杆到5倍

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # ATR指标
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=self.atr_len.value)

        # 简化的枢轴点计算
        lookback = self.lookback_len.value

        # 使用更简单的高低点识别
        dataframe["local_high"] = dataframe["high"].rolling(window=lookback).max().shift(1)
        dataframe["local_low"] = dataframe["low"].rolling(window=lookback).min().shift(1)

        # 前期高低点
        dataframe["prev_high"] = dataframe["local_high"].shift(lookback)
        dataframe["prev_low"] = dataframe["local_low"].shift(lookback)

        # ATR过滤器
        dataframe["atr_filter"] = dataframe["atr"] * self.atr_mult.value

        # 价格变动幅度
        dataframe["price_change"] = abs(
            dataframe["close"] - dataframe["close"].shift(1)
        ) / dataframe["close"].shift(1)

        # 123法则信号 - 简化版
        # 做多: 突破前期高点
        dataframe["rule_123_long"] = (
            dataframe["high"] > dataframe["local_high"] + dataframe["atr_filter"]
        ) & (dataframe["price_change"] > self.min_price_change.value)

        # 做空: 跌破前期低点
        dataframe["rule_123_short"] = (
            dataframe["low"] < dataframe["local_low"] - dataframe["atr_filter"]
        ) & (dataframe["price_change"] > self.min_price_change.value)

        # 2B法则信号 - 简化版
        # 做多: 假跌破后反弹
        dataframe["rule_2b_long"] = (
            (dataframe["low"] < dataframe["local_low"])  # 创新低
            & (dataframe["close"] > dataframe["local_low"] + dataframe["atr_filter"])  # 快速反弹
            & (dataframe["price_change"] > self.min_price_change.value)
        )

        # 做空: 假突破后回落
        dataframe["rule_2b_short"] = (
            (dataframe["high"] > dataframe["local_high"])  # 创新高
            & (dataframe["close"] < dataframe["local_high"] - dataframe["atr_filter"])  # 快速回落
            & (dataframe["price_change"] > self.min_price_change.value)
        )

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 做多条件
        dataframe.loc[(dataframe["rule_123_long"] | dataframe["rule_2b_long"]), "enter_long"] = 1

        # 做空条件
        dataframe.loc[(dataframe["rule_123_short"] | dataframe["rule_2b_short"]), "enter_short"] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 反向信号退出
        dataframe.loc[(dataframe["rule_123_short"] | dataframe["rule_2b_short"]), "exit_long"] = 1

        dataframe.loc[(dataframe["rule_123_long"] | dataframe["rule_2b_long"]), "exit_short"] = 1

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
        # 简单的ATR动态止损
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()

        if "atr" in last_candle and not pd.isna(last_candle["atr"]):
            atr_stop_distance = last_candle["atr"] * 1.5

            if trade.is_short:
                stop_price = trade.open_rate + atr_stop_distance
                return (stop_price - current_rate) / current_rate
            else:
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
        # 简单的快速止盈
        if current_profit > 0.025:  # 2.5%止盈
            return "quick_profit"

        # 持仓时间过长退出
        if (current_time - trade.open_date_utc).total_seconds() > 3600:  # 1小时
            return "timeout"

        return None
