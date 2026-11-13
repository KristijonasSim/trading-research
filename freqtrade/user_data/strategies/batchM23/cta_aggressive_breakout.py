# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file

import numpy as np
import pandas as pd
from datetime import datetime
from pandas import DataFrame
from typing import Optional

from freqtrade.strategy import (
    IStrategy,
    Trade,
    # Hyperopt
    BooleanParameter,
    CategoricalParameter,
    DecimalParameter,
    IntParameter,
    RealParameter,
    # helpers
    merge_informative_pair,
    stoploss_from_absolute,
)

import talib.abstract as ta
from technical import qtpylib


class CTAAggressiveBreakout(IStrategy):
    """
    CTA风格 - 激进通道突破（多头为主）
    - 5m 基础周期
    - 入场：Donchian 短通道向上突破 + 量能过滤（激进）
    - 退出：Chandelier/ATR 跟踪止损（不敏感，延长持仓） + 慢速 Donchian 退场
            另加极端拉升的获利了结（触发频率低）
    """

    INTERFACE_VERSION = 3
    can_short: bool = False

    # 关闭 ROI（实质上让退出依赖 custom_stoploss / exit 信号）
    minimal_roi = {"0": 10.0}

    # 初始基础止损（作为兜底；真正的退出逻辑走 custom_stoploss）
    stoploss = -0.12

    trailing_stop = False  # 使用自定义止损，不启用内置 TSL

    timeframe = "5m"
    process_only_new_candles = True

    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = True

    # 启动需要的K线数量（需覆盖最长滚动窗口）
    startup_candle_count: int = 300

    # ========== Hyperoptable params ==========
    breakout_len = IntParameter(low=15, high=40, default=20, space="buy", optimize=True, load=True)
    exit_len = IntParameter(low=25, high=80, default=35, space="sell", optimize=True, load=True)

    atr_period = IntParameter(low=7, high=35, default=14, space="sell", optimize=True, load=True)
    atr_mult = RealParameter(low=2.5, high=5.0, default=3.5, space="sell", optimize=True, load=True)

    vol_sma_period = IntParameter(low=10, high=60, default=20, space="buy", optimize=True, load=True)
    vol_mult = RealParameter(low=0.8, high=1.5, default=1.0, space="buy", optimize=True, load=True)

    rsi_exit = IntParameter(low=80, high=95, default=90, space="sell", optimize=True, load=True)
    bb_window = IntParameter(low=10, high=40, default=20, space="sell", optimize=True, load=True)

    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }
    order_time_in_force = {"entry": "GTC", "exit": "GTC"}

    plot_config = {
        "main_plot": {
            "donchian_high": {"color": "orange"},
            "donchian_low": {"color": "orange"},
            "donchian_exit": {"color": "yellow"},
            "chandelier_stop": {"color": "white"},
        },
        "subplots": {
            "ATR": {"atr": {"color": "blue"}},
            "RSI": {"rsi": {"color": "red"}},
        },
    }

    def informative_pairs(self):
        """
        如果你后续想做多周期（如1h过滤），可在此返回 [(pair, '1h'), ...]
        本策略基础版仅用 5m，避免依赖 DataProvider 的额外缓存。
        """
        return []

    # -------------- 指标计算 --------------
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        n = int(self.breakout_len.value)
        n_exit = int(self.exit_len.value)

        # Donchian 通道
        dataframe["donchian_high"] = dataframe["high"].rolling(n).max().shift(1)
        dataframe["donchian_low"] = dataframe["low"].rolling(n).min().shift(1)
        # 退出通道（更慢）
        dataframe["donchian_exit"] = dataframe["low"].rolling(n_exit).min().shift(1)

        # ATR（用于 Chandelier 止损）
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=int(self.atr_period.value))

        # RSI / Bollinger（用于爆顶退出）
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        bb = qtpylib.bollinger_bands(
            qtpylib.typical_price(dataframe), window=int(self.bb_window.value), stds=2
        )
        dataframe["bb_upper"] = bb["upper"]
        dataframe["bb_lower"] = bb["lower"]

        # 量能过滤
        dataframe["vol_sma"] = dataframe["volume"].rolling(int(self.vol_sma_period.value)).mean()

        # 画图辅助：计算当前 Chandelier 止损（基于最近 n_exit 或 n 的最高价，你也可改为更长）
        # 仅用于可视化，不参与信号（真正止损在 custom_stoploss）
        basis_h = dataframe["high"].rolling(max(n, n_exit)).max()
        dataframe["chandelier_stop"] = basis_h - self.atr_mult.value * dataframe["atr"]

        return dataframe

    # -------------- 入场 --------------
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["enter_long"] = 0

        # 新突破（close 刚刚突破上轨）
        new_breakout = (
            (dataframe["close"] > dataframe["donchian_high"]) &
            (dataframe["close"].shift(1) <= dataframe["donchian_high"].shift(1))
        )

        # 量能过滤（更激进可把 self.vol_mult 默认调到 0.9 或 0.8）
        vol_ok = dataframe["volume"] > (dataframe["vol_sma"] * float(self.vol_mult.value))

        dataframe.loc[(new_breakout & vol_ok), "enter_long"] = 1
        dataframe.loc[(new_breakout & vol_ok), "enter_tag"] = "DonchBreakout(aggr)"

        # 不做空
        if "enter_short" in dataframe.columns:
            dataframe["enter_short"] = 0

        return dataframe

    # -------------- 离场 --------------
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0

        # 1) 慢速 Donchian 退场：趋势破位才出，避免过敏
        slow_exit = dataframe["close"] < dataframe["donchian_exit"]

        # 2) 爆顶获利了结：仅在极端拉升时触发（锁定大幅盈利，非频繁）
        blowoff_exit = (dataframe["rsi"] > int(self.rsi_exit.value)) & (dataframe["close"] > dataframe["bb_upper"])

        dataframe.loc[(slow_exit | blowoff_exit), "exit_long"] = 1
        dataframe.loc[slow_exit, "exit_tag"] = "DonchExit(slow)"
        dataframe.loc[blowoff_exit, "exit_tag"] = "BlowoffTP"

        if "exit_short" in dataframe.columns:
            dataframe["exit_short"] = 0

        return dataframe

    # -------------- 自定义止损（核心：Chandelier/ATR） --------------
    def custom_stoploss(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs,
    ) -> float:
        """
        以 5m 的 ATR 与近 N 根最高价计算 Chandelier 止损，N 取 exit_len 或更大。
        通过 stoploss_from_absolute 把“绝对价位”转换为 freqtrade 需要的比例返回。
        """
        # 若 DataProvider 不可用，使用基础 stoploss 兜底
        if not hasattr(self, "dp") or self.dp is None:
            return self.stoploss

        df = self.dp.get_pair_dataframe(pair=pair, timeframe=self.timeframe)
        if df is None or df.empty:
            return self.stoploss

        # 选取当前时刻可用的最新数据
        n_exit = int(self.exit_len.value)
        atr_period = int(self.atr_period.value)

        atr = ta.ATR(df, timeperiod=atr_period)
        hh = df["high"].rolling(max(n_exit, atr_period)).max()

        # 最新值
        atr_v = float(atr.iloc[-1]) if atr.notnull().any() else None
        hh_v = float(hh.iloc[-1]) if hh.notnull().any() else None

        if atr_v is None or hh_v is None or atr_v == 0.0:
            return self.stoploss

        chandelier = hh_v - float(self.atr_mult.value) * atr_v

        # 将绝对价位转换为相对开仓价的止损比例（负数）
        desired_sl = stoploss_from_absolute(trade.open_rate, chandelier)

        # 为安全起见，若计算异常导致止损过低/过高，这里回退到基础 stoploss
        if desired_sl is None or desired_sl >= 0:
            return self.stoploss

        return desired_sl
