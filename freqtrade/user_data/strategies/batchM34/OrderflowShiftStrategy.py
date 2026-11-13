from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from freqtrade.persistence import Trade
from freqtrade.strategy import CategoricalParameter, DecimalParameter, IntParameter, IStrategy


class OrderflowShiftStrategy(IStrategy):
    """Pseudo-orderflow proxy strategy using spread, wick pressure, and relative volume shifts."""

    INTERFACE_VERSION = 3
    timeframe = "1h"
    startup_candle_count = 220
    can_short = False

    stoploss = -0.99
    minimal_roi = {"0": 10}
    use_custom_stoploss = True
    use_custom_exit = True

    rv_window = IntParameter(8, 72, default=24, space="buy", optimize=True)
    rv_spike = DecimalParameter(1.0, 5.0, default=1.9, decimals=2, space="buy", optimize=True)
    wick_ratio_min = DecimalParameter(0.8, 6.0, default=1.7, decimals=2, space="buy", optimize=True)
    spread_max = DecimalParameter(
        0.002, 0.04, default=0.012, decimals=3, space="buy", optimize=True
    )
    trend_slope_min = DecimalParameter(
        -0.004, 0.02, default=0.001, decimals=3, space="buy", optimize=True
    )
    absorption_threshold = DecimalParameter(
        0.3, 4.0, default=1.2, decimals=2, space="buy", optimize=True
    )

    sl_engine = CategoricalParameter(
        ["fixed", "atr", "vol_floor", "hybrid"], default="hybrid", space="sell", optimize=True
    )
    sl_fixed = DecimalParameter(0.02, 0.2, default=0.07, decimals=3, space="sell", optimize=True)
    sl_atr = DecimalParameter(0.5, 6.0, default=2.4, decimals=2, space="sell", optimize=True)
    sl_vol = DecimalParameter(0.5, 8.0, default=3.2, decimals=2, space="sell", optimize=True)
    sl_hybrid_weight = DecimalParameter(
        0.1, 0.9, default=0.55, decimals=2, space="sell", optimize=True
    )

    tp_engine = CategoricalParameter(
        ["fixed", "atr", "trail_buffer", "risk_reward"],
        default="trail_buffer",
        space="sell",
        optimize=True,
    )
    tp_fixed = DecimalParameter(0.01, 0.15, default=0.05, decimals=3, space="sell", optimize=True)
    tp_atr = DecimalParameter(0.8, 8.0, default=3.1, decimals=2, space="sell", optimize=True)
    tp_buffer = DecimalParameter(
        0.005, 0.12, default=0.028, decimals=3, space="sell", optimize=True
    )
    tp_rr = DecimalParameter(1.0, 6.0, default=2.2, decimals=2, space="sell", optimize=True)

    max_open_candles = IntParameter(3, 160, default=28, space="sell", optimize=True)
    age_tp_floor = DecimalParameter(
        -0.02, 0.05, default=0.004, decimals=3, space="sell", optimize=True
    )

    def populate_indicators(
        self, dataframe: pd.DataFrame, metadata: dict[str, Any]
    ) -> pd.DataFrame:
        dataframe["range"] = (dataframe["high"] - dataframe["low"]).replace(0, np.nan)
        dataframe["body"] = (dataframe["close"] - dataframe["open"]).abs()
        dataframe["upper_wick"] = dataframe["high"] - dataframe[["open", "close"]].max(axis=1)
        dataframe["lower_wick"] = dataframe[["open", "close"]].min(axis=1) - dataframe["low"]
        dataframe["wick_ratio"] = dataframe["lower_wick"] / dataframe["upper_wick"].replace(
            0, np.nan
        )
        dataframe["spread"] = dataframe["range"] / dataframe["close"]

        window = int(self.rv_window.value)
        dataframe["rel_volume"] = dataframe["volume"] / dataframe["volume"].rolling(window).mean()
        dataframe["vwap_proxy"] = (dataframe["close"] * dataframe["volume"]).rolling(
            window
        ).sum() / dataframe["volume"].rolling(window).sum()
        dataframe["price_vs_vwap"] = (dataframe["close"] - dataframe["vwap_proxy"]) / dataframe[
            "close"
        ]

        tr = pd.concat(
            [
                dataframe["high"] - dataframe["low"],
                (dataframe["high"] - dataframe["close"].shift(1)).abs(),
                (dataframe["low"] - dataframe["close"].shift(1)).abs(),
            ],
            axis=1,
        ).max(axis=1)
        dataframe["atr"] = tr.rolling(14).mean()

        dataframe["ema_fast"] = dataframe["close"].ewm(span=20, adjust=False).mean()
        dataframe["ema_slow"] = dataframe["close"].ewm(span=80, adjust=False).mean()
        dataframe["trend_slope"] = (dataframe["ema_fast"] - dataframe["ema_slow"]) / dataframe[
            "close"
        ]

        buying_pressure = (dataframe["close"] - dataframe["low"]) / dataframe["range"]
        selling_pressure = (dataframe["high"] - dataframe["close"]) / dataframe["range"]
        dataframe["absorption"] = (buying_pressure - selling_pressure) * dataframe["rel_volume"]
        dataframe["swing_low"] = dataframe["low"].rolling(15).min()
        dataframe["trail_peak"] = dataframe["high"].rolling(18).max()
        return dataframe.fillna(0)

    def populate_entry_trend(
        self, dataframe: pd.DataFrame, metadata: dict[str, Any]
    ) -> pd.DataFrame:
        signal = (
            (dataframe["rel_volume"] > float(self.rv_spike.value))
            & (dataframe["wick_ratio"] > float(self.wick_ratio_min.value))
            & (dataframe["spread"] < float(self.spread_max.value))
            & (dataframe["trend_slope"] > float(self.trend_slope_min.value))
            & (dataframe["absorption"] > float(self.absorption_threshold.value))
            & (dataframe["price_vs_vwap"] > -0.02)
            & (dataframe["volume"] > 0)
        )
        dataframe.loc[signal, ["enter_long", "enter_tag"]] = (1, "orderflow_shift")
        return dataframe

    def populate_exit_trend(
        self, dataframe: pd.DataFrame, metadata: dict[str, Any]
    ) -> pd.DataFrame:
        dataframe["exit_long"] = 0
        return dataframe

    def custom_stoploss(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        after_fill: bool,
        **kwargs: Any,
    ) -> float:
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe.empty:
            return -0.1
        row = dataframe.iloc[-1]

        engine = self.sl_engine.value
        fixed = -float(self.sl_fixed.value)
        atr_sl = -(float(row["atr"]) / current_rate) * float(self.sl_atr.value)
        vol_sl = -float(row["spread"]) * float(self.sl_vol.value)

        if engine == "fixed":
            return fixed
        if engine == "atr":
            return max(atr_sl, -0.3)
        if engine == "vol_floor":
            return max(vol_sl, -0.3)

        weight = float(self.sl_hybrid_weight.value)
        hybrid = weight * atr_sl + (1 - weight) * vol_sl
        return max(min(hybrid, -0.01), -0.3)

    def custom_exit(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs: Any,
    ) -> str | None:
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe.empty:
            return None
        row = dataframe.iloc[-1]

        candles_open = int((current_time - trade.open_date_utc).total_seconds() // 3600)
        if candles_open >= int(self.max_open_candles.value) and current_profit >= float(
            self.age_tp_floor.value
        ):
            return "time_based_tp"

        engine = self.tp_engine.value
        if engine == "fixed" and current_profit >= float(self.tp_fixed.value):
            return "tp_fixed"
        if engine == "atr":
            if (current_rate - trade.open_rate) >= float(row["atr"]) * float(self.tp_atr.value):
                return "tp_atr"
        if engine == "trail_buffer":
            trail_level = float(row["trail_peak"]) * (1 - float(self.tp_buffer.value))
            if current_rate < trail_level and current_profit > 0:
                return "tp_trail_buffer"
        if engine == "risk_reward":
            risk = abs(
                float(
                    self.custom_stoploss(
                        pair, trade, current_time, current_rate, current_profit, False
                    )
                )
            )
            if risk > 0 and current_profit >= risk * float(self.tp_rr.value):
                return "tp_rr"

        return None
