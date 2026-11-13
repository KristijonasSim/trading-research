from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from freqtrade.persistence import Trade
from freqtrade.strategy import CategoricalParameter, DecimalParameter, IntParameter, IStrategy


class FractalTunnelBreakoutStrategy(IStrategy):
    """Breakout strategy around Donchian/Keltner compression with configurable risk engines."""

    INTERFACE_VERSION = 3
    timeframe = "5m"
    startup_candle_count = 300
    can_short = False

    stoploss = -0.99
    minimal_roi = {"0": 10}
    use_custom_stoploss = True
    use_custom_exit = True

    dc_len = IntParameter(10, 80, default=34, space="buy", optimize=True)
    kc_len = IntParameter(10, 80, default=20, space="buy", optimize=True)
    kc_mult = DecimalParameter(0.8, 3.0, default=1.5, decimals=2, space="buy", optimize=True)
    squeeze_threshold = DecimalParameter(
        0.6, 1.2, default=0.9, decimals=2, space="buy", optimize=True
    )
    breakout_buffer = DecimalParameter(
        1.0, 1.02, default=1.003, decimals=3, space="buy", optimize=True
    )
    vol_multiplier = DecimalParameter(0.8, 4.0, default=1.6, decimals=2, space="buy", optimize=True)

    sl_mode = CategoricalParameter(
        ["fixed", "chandelier", "structure", "atr_step"],
        default="chandelier",
        space="sell",
        optimize=True,
    )
    sl_fixed = DecimalParameter(0.015, 0.1, default=0.04, decimals=3, space="sell", optimize=True)
    sl_chand_mult = DecimalParameter(1.0, 5.0, default=2.5, decimals=2, space="sell", optimize=True)
    sl_structure_window = IntParameter(5, 60, default=21, space="sell", optimize=True)
    sl_step_scale = DecimalParameter(0.5, 4.0, default=1.6, decimals=2, space="sell", optimize=True)

    tp_mode = CategoricalParameter(
        ["fixed", "atr", "channel", "risk_multiple"], default="channel", space="sell", optimize=True
    )
    tp_fixed = DecimalParameter(0.008, 0.08, default=0.025, decimals=3, space="sell", optimize=True)
    tp_atr_mult = DecimalParameter(0.8, 6.0, default=2.8, decimals=2, space="sell", optimize=True)
    tp_channel_factor = DecimalParameter(
        0.4, 2.5, default=1.2, decimals=2, space="sell", optimize=True
    )
    tp_risk_mult = DecimalParameter(1.0, 5.0, default=2.0, decimals=2, space="sell", optimize=True)

    candles_to_force_exit = IntParameter(12, 300, default=96, space="sell", optimize=True)
    candles_to_force_profit = DecimalParameter(
        -0.01, 0.04, default=0.003, decimals=3, space="sell", optimize=True
    )

    def populate_indicators(
        self, dataframe: pd.DataFrame, metadata: dict[str, Any]
    ) -> pd.DataFrame:
        tr_components = pd.concat(
            [
                dataframe["high"] - dataframe["low"],
                (dataframe["high"] - dataframe["close"].shift(1)).abs(),
                (dataframe["low"] - dataframe["close"].shift(1)).abs(),
            ],
            axis=1,
        )
        dataframe["tr"] = tr_components.max(axis=1)
        dataframe["atr"] = dataframe["tr"].rolling(14).mean()

        dc = int(self.dc_len.value)
        dataframe["dc_high"] = dataframe["high"].rolling(dc).max()
        dataframe["dc_low"] = dataframe["low"].rolling(dc).min()
        dataframe["dc_width"] = (dataframe["dc_high"] - dataframe["dc_low"]) / dataframe["close"]

        ema = dataframe["close"].ewm(span=int(self.kc_len.value), adjust=False).mean()
        dataframe["kc_upper"] = ema + dataframe["atr"] * float(self.kc_mult.value)
        dataframe["kc_lower"] = ema - dataframe["atr"] * float(self.kc_mult.value)
        dataframe["kc_width"] = (dataframe["kc_upper"] - dataframe["kc_lower"]) / dataframe["close"]

        dataframe["squeeze_ratio"] = dataframe["dc_width"] / dataframe["kc_width"].replace(
            0, np.nan
        )
        dataframe["vol_ma"] = dataframe["volume"].rolling(30).mean()
        dataframe["hh_structure"] = (
            dataframe["high"].rolling(int(self.sl_structure_window.value)).max()
        )
        dataframe["ll_structure"] = (
            dataframe["low"].rolling(int(self.sl_structure_window.value)).min()
        )
        return dataframe

    def populate_entry_trend(
        self, dataframe: pd.DataFrame, metadata: dict[str, Any]
    ) -> pd.DataFrame:
        squeezed = dataframe["squeeze_ratio"] < float(self.squeeze_threshold.value)
        breakout = dataframe["close"] > dataframe["dc_high"].shift(1) * float(
            self.breakout_buffer.value
        )
        volume_ok = dataframe["volume"] > dataframe["vol_ma"] * float(self.vol_multiplier.value)
        dataframe.loc[squeezed & breakout & volume_ok, ["enter_long", "enter_tag"]] = (
            1,
            "fractal_breakout",
        )
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
            return -0.08
        row = dataframe.iloc[-1]

        mode = self.sl_mode.value
        if mode == "fixed":
            return -float(self.sl_fixed.value)
        if mode == "chandelier":
            stop_price = float(row["hh_structure"]) - float(row["atr"]) * float(
                self.sl_chand_mult.value
            )
            return (stop_price / current_rate) - 1
        if mode == "structure":
            stop_price = float(row["ll_structure"])
            return (stop_price / current_rate) - 1

        dynamic = -float(row["atr"] / current_rate) * float(self.sl_step_scale.value)
        return max(dynamic, -0.2)

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

        candles_open = int((current_time - trade.open_date_utc).total_seconds() // (5 * 60))
        if candles_open >= int(self.candles_to_force_exit.value) and current_profit >= float(
            self.candles_to_force_profit.value
        ):
            return "candle_time_tp"

        mode = self.tp_mode.value
        if mode == "fixed" and current_profit >= float(self.tp_fixed.value):
            return "tp_fixed"
        if mode == "atr":
            target = float(row["atr"]) * float(self.tp_atr_mult.value)
            if (current_rate - trade.open_rate) >= target:
                return "tp_atr"
        if mode == "channel":
            channel_size = float(row["dc_high"] - row["dc_low"])
            if (current_rate - trade.open_rate) >= channel_size * float(
                self.tp_channel_factor.value
            ):
                return "tp_channel"
        if mode == "risk_multiple":
            risk = abs(
                float(
                    self.custom_stoploss(
                        pair, trade, current_time, current_rate, current_profit, False
                    )
                )
            )
            if risk > 0 and current_profit >= risk * float(self.tp_risk_mult.value):
                return "tp_risk"

        return None
