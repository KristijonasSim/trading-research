# best_strategy_so_far.py
# ============================================================================
# MAINTAINED COPY of the project's current best validated strategy, per
# PROJECT_OPERATOR_MANUAL.md. Replace ONLY if a new strategy demonstrates
# superior ROBUSTNESS (not merely higher historical returns).
#
# Current holder: TrendVolTarget (adopted 2026-06-11, unbeaten through 2026-07-08)
# Canonical/live file: user_data/strategies/TrendVolTarget.py (identical logic)
#
# Status (2026-07-08):
#   - Full-window 6.5y BTC+ETH (real engine): +458%, Sharpe 1.26, MaxDD -16.6%
#   - Held-out TEST (mid-2024..2026): Sharpe 0.41 — only construct in the
#     project with clearly positive OOS
#   - Deflated Sharpe Ratio: 0.64-0.67 at n_trials=85 (bar: 0.95) — the edge is
#     ~64% credible after multiple-testing correction, NOT statistically proven
#   - Honest forward expectation: 5-15% CAGR at ~20% MaxDD
#   - Edge mechanism: bear-regime avoidance + vol-target sizing, not prediction
#   - DRY-RUN ONLY. Do not deploy real capital on backtest evidence.
# ============================================================================
#
# Design (all components individually plateau-robust, see user_data/research/):
#   Core entry (3-of-3 trend agreement, per asset):
#     close > SMA200  AND  ROC30 > 0  AND  EMA20 > EMA50
#   Exit: any core condition breaks.
#   Sizing: vol-targeted — stake scaled by clip(40% / realized_vol_30d, 0, 1),
#     quantized to 25% steps, max 50% of equity per pair (BTC + ETH basket).
#
# Freqtrade 2026.x | OKX spot | dry-run only.

from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
from pandas import DataFrame

from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy


class TrendVolTarget(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "1d"
    startup_candle_count: int = 250

    # Trend exit is the primary risk control; stop is a disaster brake only.
    stoploss = -0.30
    use_custom_stoploss = False
    trailing_stop = False

    # Exits handled by signal, not ROI.
    minimal_roi = {"0": 100.0}
    use_exit_signal = True
    exit_profit_only = False

    # Allow rebalancing as vol scale changes
    position_adjustment_enable = True
    max_entry_position_adjustment = 8

    # Vol-target parameters (plateau-robust 30-50%; 40% chosen mid-plateau)
    VOL_TARGET = 0.40
    VOL_LOOKBACK = 30
    QUANT_STEP = 0.25
    PER_PAIR_CAP = 0.50  # max fraction of total equity per pair (2-pair basket)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        c = dataframe["close"]
        dataframe["sma200"] = c.rolling(200).mean()
        dataframe["roc30"] = c.pct_change(30)
        dataframe["ema20"] = c.ewm(span=20, adjust=False).mean()
        dataframe["ema50"] = c.ewm(span=50, adjust=False).mean()
        rv = c.pct_change().rolling(self.VOL_LOOKBACK).std() * np.sqrt(365)
        scale = (self.VOL_TARGET / rv).clip(0, 1)
        # quantize to 25% steps
        dataframe["vt_scale"] = (scale / self.QUANT_STEP).round() * self.QUANT_STEP
        dataframe["core"] = (
            (c > dataframe["sma200"])
            & (dataframe["roc30"] > 0)
            & (dataframe["ema20"] > dataframe["ema50"])
        ).astype(int)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["core"] == 1) & (dataframe["vt_scale"] > 0) & (dataframe["volume"] > 0),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["core"] == 0, "exit_long"] = 1
        return dataframe

    # ---- vol-targeted stake sizing ----

    def _desired_fraction(self, pair: str, current_time: datetime) -> float:
        """Target fraction of total equity for this pair right now."""
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if df is None or df.empty:
            return 0.0
        row = df.iloc[-1]
        if row.get("core", 0) != 1:
            return 0.0
        scale = float(row.get("vt_scale", 0.0))
        return max(0.0, min(1.0, scale)) * self.PER_PAIR_CAP

    def custom_stake_amount(
        self, pair: str, current_time: datetime, current_rate: float,
        proposed_stake: float, min_stake: Optional[float], max_stake: float,
        leverage: float, entry_tag: Optional[str], side: str, **kwargs,
    ) -> float:
        frac = self._desired_fraction(pair, current_time)
        if frac <= 0:
            return 0.0
        total = self.wallets.get_total_stake_amount()
        stake = total * frac
        return max(min_stake or 0.0, min(stake, max_stake))

    def adjust_trade_position(
        self, trade: Trade, current_time: datetime, current_rate: float,
        current_profit: float, min_stake: Optional[float], max_stake: float,
        current_entry_rate: float, current_exit_rate: float,
        current_entry_profit: float, current_exit_profit: float, **kwargs,
    ) -> Optional[float]:
        """Rebalance stake toward the vol-target as the scale changes (25% steps)."""
        frac = self._desired_fraction(trade.pair, current_time)
        total = self.wallets.get_total_stake_amount()
        desired = total * frac
        current = trade.stake_amount
        # only act when drift exceeds half a quantization step of per-pair equity
        threshold = total * self.PER_PAIR_CAP * self.QUANT_STEP / 2
        diff = desired - current
        if abs(diff) < threshold:
            return None
        if diff > 0:
            return min(diff, max_stake - current)
        # negative = partial exit
        return max(diff, -current * 0.9)
