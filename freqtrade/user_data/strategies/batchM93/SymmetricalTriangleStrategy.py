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

from freqtrade.strategy import (
    IStrategy,
    IntParameter,
    DecimalParameter,
    CategoricalParameter,
    stoploss_from_open,
)
from freqtrade.persistence import Trade

import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib


class EnhancedRule123And2BStrategy(IStrategy):
    """
    增强版123法则 & 2B法则策略
    添加趋势确认、成交量验证和改进的风险管理
    """

    INTERFACE_VERSION = 3
    timeframe = "5m"
    can_short: bool = True

    # 优化ROI设置
    minimal_roi = {"0": 0.03, "30": 0.02, "60": 0.01, "120": 0}

    # 止损设置
    stoploss = -0.02
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02
    trailing_only_offset_is_reached = True

    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    startup_candle_count: int = 50

    # 策略参数
    lookback_len = IntParameter(8, 20, default=12, space="buy", optimize=True)
    atr_len = IntParameter(10, 25, default=14, space="buy", optimize=True)
    atr_mult = DecimalParameter(0.1, 0.5, default=0.2, space="buy", optimize=True)
    min_price_change = DecimalParameter(0.005, 0.03, default=0.01, space="buy", optimize=True)

    # 新增参数
    trend_ema_len = IntParameter(20, 50, default=34, space="buy", optimize=True)
    volume_factor = DecimalParameter(1.0, 2.5, default=1.5, space="buy", optimize=True)
    min_trend_strength = DecimalParameter(0.5, 2.0, default=1.0, space="buy", optimize=True)

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
        return min(proposed_leverage, 5.0)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 基础指标
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=self.atr_len.value)

        # 趋势指标
        dataframe["ema"] = ta.EMA(dataframe, timeperiod=self.trend_ema_len.value)
        dataframe["adx"] = ta.ADX(dataframe)

        # 成交量指标
        dataframe["volume_ma"] = ta.SMA(dataframe["volume"], timeperiod=20)
        dataframe["volume_ratio"] = dataframe["volume"] / dataframe["volume_ma"]

        # 价格波动指标
        dataframe["price_change"] = abs(
            dataframe["close"] - dataframe["close"].shift(1)
        ) / dataframe["close"].shift(1)

        # 枢轴点识别
        lookback = self.lookback_len.value
        dataframe["local_high"] = dataframe["high"].rolling(window=lookback).max().shift(1)
        dataframe["local_low"] = dataframe["low"].rolling(window=lookback).min().shift(1)

        # 前期高低点
        dataframe["prev_high"] = (
            dataframe["high"].rolling(window=lookback * 2).max().shift(lookback)
        )
        dataframe["prev_low"] = dataframe["low"].rolling(window=lookback * 2).min().shift(lookback)

        # ATR过滤器
        dataframe["atr_filter"] = dataframe["atr"] * self.atr_mult.value

        # 趋势方向判断
        dataframe["trend_direction"] = np.where(dataframe["close"] > dataframe["ema"], 1, -1)
        dataframe["trend_strength"] = dataframe["adx"] / 100  # 标准化到0-1范围

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 趋势强度过滤
        trend_condition = dataframe["trend_strength"] >= (self.min_trend_strength.value / 100)

        # 成交量确认
        volume_condition = dataframe["volume_ratio"] >= self.volume_factor.value

        # 价格变动过滤
        price_change_condition = dataframe["price_change"] > self.min_price_change.value

        # 123法则信号 - 增强版
        # 做多: 突破前期高点 + 趋势向上确认
        dataframe["rule_123_long"] = (
            (dataframe["high"] > dataframe["local_high"] + dataframe["atr_filter"])
            & (dataframe["close"] > dataframe["ema"])
            & trend_condition
            & volume_condition
            & price_change_condition
        )

        # 做空: 跌破前期低点 + 趋势向下确认
        dataframe["rule_123_short"] = (
            (dataframe["low"] < dataframe["local_low"] - dataframe["atr_filter"])
            & (dataframe["close"] < dataframe["ema"])
            & trend_condition
            & volume_condition
            & price_change_condition
        )

        # 2B法则信号 - 增强版
        # 做多: 假跌破后反弹 + 成交量确认
        dataframe["rule_2b_long"] = (
            (dataframe["low"] < dataframe["local_low"])  # 创新低
            & (dataframe["close"] > dataframe["local_low"] + dataframe["atr_filter"])  # 快速反弹
            & (dataframe["close"] > dataframe["open"])  # 阳线确认
            & (dataframe["close"] > dataframe["ema"])  # 在均线上方
            & volume_condition
            & price_change_condition
        )

        # 做空: 假突破后回落 + 成交量确认
        dataframe["rule_2b_short"] = (
            (dataframe["high"] > dataframe["local_high"])  # 创新高
            & (dataframe["close"] < dataframe["local_high"] - dataframe["atr_filter"])  # 快速回落
            & (dataframe["close"] < dataframe["open"])  # 阴线确认
            & (dataframe["close"] < dataframe["ema"])  # 在均线下方
            & volume_condition
            & price_change_condition
        )

        # 设置入场信号
        dataframe.loc[(dataframe["rule_123_long"] | dataframe["rule_2b_long"]), "enter_long"] = 1

        dataframe.loc[(dataframe["rule_123_short"] | dataframe["rule_2b_short"]), "enter_short"] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 基于趋势反转的退出信号
        dataframe.loc[
            (
                (dataframe["close"] < dataframe["ema"])  # 跌破均线
                & (
                    dataframe["trend_strength"] >= (self.min_trend_strength.value / 100)
                )  # 趋势强度足够
            ),
            "exit_long",
        ] = 1

        dataframe.loc[
            (
                (dataframe["close"] > dataframe["ema"])  # 升破均线
                & (
                    dataframe["trend_strength"] >= (self.min_trend_strength.value / 100)
                )  # 趋势强度足够
            ),
            "exit_short",
        ] = 1

        return dataframe

    def custom_stoploss(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        after_fill: bool,
        **kwargs,
    ) -> float | None:
        # 动态ATR止损,随盈利增加而收紧
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()

        if "atr" in last_candle and not pd.isna(last_candle["atr"]):
            # 基础ATR止损
            atr_stop_distance = last_candle["atr"] * 2.0

            # 盈利时收紧止损
            if current_profit > 0:
                atr_stop_distance = last_candle["atr"] * max(1.5 - (current_profit * 10), 0.5)

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
        # 盈利目标退出
        if current_profit > 0.05:  # 5%止盈
            return "take_profit"

        # 时间基退出
        if (current_time - trade.open_date_utc).total_seconds() > 7200:  # 2小时
            return "time_exit"

        return None
