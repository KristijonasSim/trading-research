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


class AdaptiveRegimeRotationStrategy(IStrategy):
    """
    Regime-aware momentum/mean-reversion hybrid.

    - Detects trend regime with EMA spread and ADX.
    - In trend regime it buys pullbacks.
    - In range regime it buys Bollinger lower-band sweeps.
    - Uses selectable stoploss engines and selectable TP engines.
    - Adds candle-age based profit taking (time-based in candles).
    """

    INTERFACE_VERSION = 3
    can_short = False
    timeframe = "15m"
    startup_candle_count = 240

    stoploss = -0.99
    minimal_roi = {"0": 10}
    use_custom_stoploss = True
    use_custom_exit = True

    buy_adx_floor = IntParameter(10, 35, default=18, space="buy", optimize=True)
    buy_regime_gap = DecimalParameter(
        0.002, 0.03, default=0.008, decimals=3, space="buy", optimize=True
    )
    buy_rsi_pullback = IntParameter(20, 55, default=42, space="buy", optimize=True)
    buy_bb_buffer = DecimalParameter(
        0.97, 1.01, default=0.995, decimals=3, space="buy", optimize=True
    )
    buy_mfi_cap = IntParameter(20, 70, default=52, space="buy", optimize=True)

    stop_mode = CategoricalParameter(
        ["fixed", "atr_band", "swing", "volatility"],
        default="atr_band",
        space="sell",
        optimize=True,
    )
    sl_fixed = DecimalParameter(0.02, 0.15, default=0.06, decimals=3, space="sell", optimize=True)
    sl_atr_mult = DecimalParameter(0.8, 4.0, default=2.0, decimals=2, space="sell", optimize=True)
    sl_swing_buffer = DecimalParameter(
        0.005, 0.04, default=0.012, decimals=3, space="sell", optimize=True
    )
    sl_volatility_mult = DecimalParameter(
        1.0, 5.0, default=2.5, decimals=2, space="sell", optimize=True
    )

    tp_mode = CategoricalParameter(
        ["percent", "atr_multiple", "rr"], default="percent", space="sell", optimize=True
    )
    tp_percent = DecimalParameter(
        0.01, 0.12, default=0.035, decimals=3, space="sell", optimize=True
    )
    tp_atr_mult = DecimalParameter(0.8, 5.0, default=2.2, decimals=2, space="sell", optimize=True)
    tp_rr = DecimalParameter(1.0, 4.0, default=1.8, decimals=2, space="sell", optimize=True)

    time_tp_candles = IntParameter(8, 192, default=64, space="sell", optimize=True)
    time_tp_min_profit = DecimalParameter(
        -0.01, 0.04, default=0.006, decimals=3, space="sell", optimize=True
    )

    def populate_indicators(
        self, dataframe: pd.DataFrame, metadata: dict[str, Any]
    ) -> pd.DataFrame:
        dataframe["ema_fast"] = dataframe["close"].ewm(span=21, adjust=False).mean()
        dataframe["ema_slow"] = dataframe["close"].ewm(span=120, adjust=False).mean()
        dataframe["ema_mid"] = dataframe["close"].ewm(span=55, adjust=False).mean()

        tr_components = pd.concat(
            [
                (dataframe["high"] - dataframe["low"]).abs(),
                (dataframe["high"] - dataframe["close"].shift(1)).abs(),
                (dataframe["low"] - dataframe["close"].shift(1)).abs(),
            ],
            axis=1,
        )
        dataframe["tr"] = tr_components.max(axis=1)
        dataframe["atr"] = dataframe["tr"].rolling(14).mean()
        dataframe["volatility"] = (
            dataframe["close"].pct_change().rolling(48).std() * np.sqrt(48)
        ).fillna(0)

        up_move = dataframe["high"].diff()
        down_move = -dataframe["low"].diff()
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
        atr = dataframe["tr"].rolling(14).mean().replace(0, np.nan)
        plus_di = 100 * pd.Series(plus_dm, index=dataframe.index).rolling(14).sum() / atr
        minus_di = 100 * pd.Series(minus_dm, index=dataframe.index).rolling(14).sum() / atr
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
        dataframe["adx"] = dx.rolling(14).mean().fillna(0)

        delta = dataframe["close"].diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        dataframe["rsi"] = 100 - (100 / (1 + rs))

        tp = (dataframe["high"] + dataframe["low"] + dataframe["close"]) / 3
        rmf = tp * dataframe["volume"]
        pos_mf = rmf.where(tp > tp.shift(1), 0.0).rolling(14).sum()
        neg_mf = rmf.where(tp < tp.shift(1), 0.0).rolling(14).sum().replace(0, np.nan)
        mfr = pos_mf / neg_mf
        dataframe["mfi"] = 100 - (100 / (1 + mfr))

        bb_mid = dataframe["close"].rolling(20).mean()
        bb_std = dataframe["close"].rolling(20).std()
        dataframe["bb_lower"] = bb_mid - 2 * bb_std

        dataframe["swing_low"] = dataframe["low"].rolling(18).min()
        dataframe["ema_gap"] = (dataframe["ema_fast"] - dataframe["ema_slow"]) / dataframe["close"]
        dataframe["regime_trending"] = (
            (dataframe["ema_gap"] > self.buy_regime_gap.value)
            & (dataframe["adx"] > self.buy_adx_floor.value)
        ).astype(int)
        return dataframe

    def populate_entry_trend(
        self, dataframe: pd.DataFrame, metadata: dict[str, Any]
    ) -> pd.DataFrame:
        trend_pullback = (
            (dataframe["regime_trending"] == 1)
            & (dataframe["close"] > dataframe["ema_slow"])
            & (dataframe["close"] < dataframe["ema_mid"])
            & (dataframe["rsi"] < self.buy_rsi_pullback.value)
            & (dataframe["volume"] > 0)
        )
        range_reversion = (
            (dataframe["regime_trending"] == 0)
            & (dataframe["close"] < dataframe["bb_lower"] * self.buy_bb_buffer.value)
            & (dataframe["mfi"] < self.buy_mfi_cap.value)
            & (dataframe["volume"] > 0)
        )

        dataframe.loc[trend_pullback | range_reversion, ["enter_long", "enter_tag"]] = (
            1,
            "regime_rotation",
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
            return -0.10
        last = dataframe.iloc[-1]

        mode = self.stop_mode.value
        if mode == "fixed":
            return -float(self.sl_fixed.value)
        if mode == "atr_band":
            sl_price = current_rate - float(last["atr"]) * float(self.sl_atr_mult.value)
            return (sl_price / current_rate) - 1
        if mode == "swing":
            swing_sl_price = float(last["swing_low"]) * (1 - float(self.sl_swing_buffer.value))
            return (swing_sl_price / current_rate) - 1

        vol_sl = -float(last["volatility"]) * float(self.sl_volatility_mult.value)
        return max(vol_sl, -0.25)

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
        last = dataframe.iloc[-1]

        candles_open = int((current_time - trade.open_date_utc).total_seconds() // (15 * 60))
        if candles_open >= int(self.time_tp_candles.value) and current_profit >= float(
            self.time_tp_min_profit.value
        ):
            return "time_tp"

        tp_mode = self.tp_mode.value
        if tp_mode == "percent":
            if current_profit >= float(self.tp_percent.value):
                return "tp_percent"
        elif tp_mode == "atr_multiple":
            atr_target = float(last["atr"]) * float(self.tp_atr_mult.value)
            if (current_rate - trade.open_rate) >= atr_target:
                return "tp_atr"
        else:
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
