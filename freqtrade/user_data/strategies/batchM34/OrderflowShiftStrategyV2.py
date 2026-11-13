from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from freqtrade.persistence import Trade
from freqtrade.strategy import (
    CategoricalParameter,
    DecimalParameter,
    IntParameter,
    IStrategy,
)


class OrderflowShiftStrategyV2(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "1h"
    startup_candle_count = 220
    can_short = False

    stoploss = -0.99
    minimal_roi = {"0": 100}
    use_custom_stoploss = True
    use_custom_exit = True

    # ===== BUY (6) =====
    rv_window = IntParameter(12, 60, default=24, space="buy", optimize=True)
    rv_spike = DecimalParameter(1.2, 4.0, default=1.9, decimals=2, space="buy", optimize=True)
    wick_ratio_min = DecimalParameter(1.0, 5.0, default=1.7, decimals=2, space="buy", optimize=True)
    spread_max = DecimalParameter(
        0.003, 0.03, default=0.012, decimals=3, space="buy", optimize=True
    )
    trend_slope_min = DecimalParameter(
        -0.002, 0.015, default=0.001, decimals=3, space="buy", optimize=True
    )
    absorption_threshold = DecimalParameter(
        0.5, 3.5, default=1.2, decimals=2, space="buy", optimize=True
    )

    # ===== SELL (6) =====
    sl_engine = CategoricalParameter(["fixed", "atr"], default="atr", space="sell", optimize=True)
    sl_value = DecimalParameter(0.02, 0.15, default=0.06, decimals=3, space="sell", optimize=True)

    tp_engine = CategoricalParameter(["atr", "rr"], default="atr", space="sell", optimize=True)
    tp_value = DecimalParameter(1.0, 4.0, default=2.0, decimals=2, space="sell", optimize=True)

    max_open_candles = IntParameter(12, 96, default=36, space="sell", optimize=True)
    age_tp_floor = DecimalParameter(
        -0.01, 0.02, default=0.002, decimals=3, space="sell", optimize=True
    )

    # =========================================================

    def populate_indicators(
        self, dataframe: pd.DataFrame, metadata: dict[str, Any]
    ) -> pd.DataFrame:

        dataframe["range"] = (dataframe["high"] - dataframe["low"]).replace(0, np.nan)
        dataframe["upper_wick"] = dataframe["high"] - dataframe[["open", "close"]].max(axis=1)
        dataframe["lower_wick"] = dataframe[["open", "close"]].min(axis=1) - dataframe["low"]
        dataframe["wick_ratio"] = dataframe["lower_wick"] / dataframe["upper_wick"].replace(
            0, np.nan
        )
        dataframe["spread"] = dataframe["range"] / dataframe["close"]

        tr = pd.concat(
            [
                dataframe["high"] - dataframe["low"],
                (dataframe["high"] - dataframe["close"].shift(1)).abs(),
                (dataframe["low"] - dataframe["close"].shift(1)).abs(),
            ],
            axis=1,
        ).max(axis=1)

        dataframe["atr"] = tr.rolling(14).mean()

        ema_fast = dataframe["close"].ewm(span=20, adjust=False).mean()
        ema_slow = dataframe["close"].ewm(span=80, adjust=False).mean()
        dataframe["trend_slope"] = (ema_fast - ema_slow) / dataframe["close"]

        dataframe.fillna(0, inplace=True)
        return dataframe

    # =========================================================

    def populate_entry_trend(
        self, dataframe: pd.DataFrame, metadata: dict[str, Any]
    ) -> pd.DataFrame:

        window = int(self.rv_window.value)

        rel_volume = dataframe["volume"] / dataframe["volume"].rolling(window).mean()

        buying_pressure = (dataframe["close"] - dataframe["low"]) / dataframe["range"].replace(
            0, np.nan
        )
        selling_pressure = (dataframe["high"] - dataframe["close"]) / dataframe["range"].replace(
            0, np.nan
        )

        absorption = (buying_pressure - selling_pressure) * rel_volume

        signal = (
            (rel_volume > float(self.rv_spike.value))
            & (dataframe["wick_ratio"] > float(self.wick_ratio_min.value))
            & (dataframe["spread"] < float(self.spread_max.value))
            & (dataframe["trend_slope"] > float(self.trend_slope_min.value))
            & (absorption > float(self.absorption_threshold.value))
            & (dataframe["volume"] > 0)
        )

        dataframe.loc[signal, "enter_long"] = 1
        return dataframe

    # =========================================================

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
        row = dataframe.iloc[-1]

        if self.sl_engine.value == "fixed":
            sl = -float(self.sl_value.value)
        else:
            sl = -(float(row["atr"]) / current_rate) * float(self.sl_value.value)

        return max(sl, -0.15)

    # =========================================================

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
        row = dataframe.iloc[-1]

        candles_open = int((current_time - trade.open_date_utc).total_seconds() // 3600)

        if candles_open >= int(self.max_open_candles.value) and current_profit >= float(
            self.age_tp_floor.value
        ):
            return "time_exit"

        if self.tp_engine.value == "atr":
            if (current_rate - trade.open_rate) >= float(row["atr"]) * float(self.tp_value.value):
                return "tp_atr"

        else:
            risk = abs(
                self.custom_stoploss(pair, trade, current_time, current_rate, current_profit, False)
            )
            if risk > 0 and current_profit >= risk * float(self.tp_value.value):
                return "tp_rr"

        return None

    def populate_exit_trend(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:

        dataframe["exit_long"] = 0
        return dataframe
