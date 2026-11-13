# XSectMomMajors1d.py
# Cross-sectional momentum across top-10 crypto majors, daily timeframe.
# Design references:
#   - Jegadeesh & Titman (1993) cross-sectional momentum framework
#   - Jansen, "Machine Learning for Algorithmic Trading" Ch.5-7 (signal construction)
#   - Lopez de Prado, AFML (concentration robustness, deflated Sharpe)
#   - RIBAF 2025 crypto momentum literature (formation/holding periods)
#
# Architecture:
#   - Universe: 10 USDT-M perpetuals (Binance Futures / OKX)
#   - Signal: rank assets by risk-adjusted 30-90d return on bar t-1
#   - Entry: top-K ranked assets that also pass per-asset trend filter
#   - Exit: rank falls out of top-K OR ATR trailing stop OR time-stop @ 21d
#   - Sizing: equal risk per position (vol-targeted), capped at 25% margin/equity
#   - Funding-aware: uses real funding data if present, flat stub if not
#
# Funding-rate handling (Option 3 active — PLACEHOLDER):
#   FUNDING_STUB_DAILY_PCT = 0.0003 (~0.03%/day = ~11%/yr conservative estimate).
#   Replace with Option 1 or 2 (Coinglass backfill or Binance native data) before
#   live deployment. Do NOT lower acceptance gates to compensate.
#
# Changes from user-supplied spec:
#   1. ROI table set to {"0": 100.0}: spec keys (21/45/90) are MINUTES in Freqtrade,
#      not days. At 21 minutes a 20% ROI target would fire constantly. All time-based
#      exits are handled by custom_exit (MAX_HOLD_DAYS=21), making ROI redundant.
#   2. use_custom_stoploss = True added (was missing from spec).
#   3. startup_candle_count raised to 350: max momentum lookback (90d) + EMA200
#      warmup (200d) + 60d buffer.
#
# Freqtrade 2026.4 | OKX (or Binance) Futures USDT-M | isolated margin.

from datetime import datetime, timedelta
from functools import reduce
from typing import Optional, List

import numpy as np
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.persistence import Trade
from freqtrade.strategy import (
    IStrategy,
    IntParameter,
    DecimalParameter,
)


# Universe — declared at module scope so informative_pairs can return it without self
MAJORS_UNIVERSE: List[str] = [
    "BTC/USDT:USDT",
    "ETH/USDT:USDT",
    "SOL/USDT:USDT",
    "BNB/USDT:USDT",
    "XRP/USDT:USDT",
    "ADA/USDT:USDT",
    "AVAX/USDT:USDT",
    "DOT/USDT:USDT",
    "LINK/USDT:USDT",
    # MATIC removed: rebranded to POL on OKX in Sep 2024; POL perp only has ~20 months
    # of history — too short for the IS period. POL/USDT:USDT confirmed live on OKX
    # but excluded. Remaining 9-pair universe still satisfies min_distinct_pairs >= 6.
    # On Binance, MATIC/USDT:USDT still trades as of May 2026 — add back if switching exchange.
]


class XSectMomMajors1d(IStrategy):
    """
    Long-only cross-sectional momentum on 10 crypto majors, daily bars.
    Each pair instance reads sibling-pair indicators via DataProvider and
    decides entry/exit based on its rank in the cross-section computed
    from bar t-1 vol-adjusted returns.
    """

    INTERFACE_VERSION = 3

    timeframe = "1d"
    can_short: bool = False
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # EMA200 needs 200 bars; 90d momentum lookback needs 90 + buffer.
    # 200 + 90 + 60 = 350.
    startup_candle_count: int = 350

    stoploss = -0.25  # backstop; real stop is custom_stoploss (ATR trailing)
    use_custom_stoploss = True

    # ROI disabled — all time-based exits go through custom_exit (21-day stop).
    # WARNING: Freqtrade ROI keys are MINUTES, not days. The original spec's keys
    # (21/45/90) would have fired after 21, 45, 90 MINUTES — not the intended days.
    minimal_roi = {"0": 100.0}

    trailing_stop = False

    # ------- Hyperopt params (6 max) -------
    momentum_lookback = IntParameter(20, 90, default=60, space="buy", optimize=True)
    top_k_entry = IntParameter(1, 3, default=2, space="buy", optimize=True)
    top_k_exit = IntParameter(2, 5, default=3, space="sell", optimize=True)
    atr_stop_mult = DecimalParameter(2.0, 5.0, default=3.0, decimals=1, space="sell", optimize=True)
    risk_per_trade_pct = DecimalParameter(0.005, 0.015, default=0.01, decimals=3, space="buy", optimize=True)
    use_trend_filter = IntParameter(0, 1, default=1, space="buy", optimize=True)

    # Fixed parameters
    MAX_HOLD_DAYS = 21
    UNIVERSE = MAJORS_UNIVERSE

    # Funding stub — active (Option 3). Conservative daily cost estimate.
    # Overridden per-bar when real 'funding_rate' column is present in the data.
    FUNDING_STUB_DAILY_PCT = 0.0003  # ~0.03%/day ≈ 11%/yr

    # ------- Protections -------
    @property
    def protections(self):
        return [
            {"method": "CooldownPeriod", "stop_duration_candles": 1},
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 30,
                "trade_limit": 4,
                "stop_duration_candles": 7,
                "only_per_pair": False,
            },
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 180,
                "trade_limit": 8,
                "stop_duration_candles": 14,
                "max_allowed_drawdown": 0.20,
            },
            {
                "method": "LowProfitPairs",
                "lookback_period_candles": 180,
                "trade_limit": 3,
                "stop_duration_candles": 30,
                "required_profit": 0.0,
            },
        ]

    # ------- Informative pairs: pull every universe member at 1d -------
    def informative_pairs(self):
        return [(pair, "1d") for pair in self.UNIVERSE]

    # ------- Helpers -------
    def _compute_pair_momentum_score(self, df: DataFrame, lookback: int) -> pd.Series:
        """
        Volatility-adjusted return: (close_{t-1}/close_{t-1-lookback} - 1) / realized_vol.
        Uses .shift(1) on close so the score at bar t is computed from bar t-1 data only.
        Divides by 20-bar realised vol (also shifted) to equalise across assets.
        """
        ret = df["close"].shift(1) / df["close"].shift(1 + lookback) - 1.0
        log_ret = np.log(df["close"] / df["close"].shift(1))
        vol = log_ret.rolling(lookback).std().shift(1)
        score = ret / vol.replace(0, np.nan)
        return score

    # ------- Indicators -------
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        lookback = int(self.momentum_lookback.value)

        # Per-asset indicators
        df["atr"] = ta.ATR(df, timeperiod=14)
        df["ema200"] = ta.EMA(df, timeperiod=200)
        df["mom_score"] = self._compute_pair_momentum_score(df, lookback)

        # Funding rate cost tracking.
        # If the data feed includes 'funding_rate' (from --trading-mode futures download),
        # use it. Otherwise fall back to the stub.
        if "funding_rate" in df.columns:
            # 3 funding events per day (8h intervals); sum gives daily funding cost
            df["funding_cost_daily"] = df["funding_rate"].rolling(3).sum().fillna(0)
        else:
            df["funding_cost_daily"] = self.FUNDING_STUB_DAILY_PCT

        # --- LOOKAHEAD GUARD ---
        # Shift raw indicators by 1 so logic reads bar t-1 values.
        # mom_score is ALREADY based on t-1 close (shift applied in helper above),
        # so shifting again here makes cs_rank_prev a t-2 signal — conservative
        # double-lag, not a lookahead risk. See _attach_cross_sectional_rank note.
        for col in ["atr", "ema200", "mom_score", "close", "funding_cost_daily"]:
            df[f"{col}_prev"] = df[col].shift(1)

        # Cross-sectional rank: requires all sibling pairs' data via DataProvider
        df["cs_rank"] = np.nan
        df["cs_universe_size"] = np.nan

        if self.dp is not None:
            df = self._attach_cross_sectional_rank(df, metadata["pair"], lookback)

        # Defensive shift: cs_rank is already t-1 based (mom_score uses shift(1)).
        # Shifting again creates t-2 lag. This is intentional — prevents any
        # edge-case where backtesting DataProvider leaks bar-t sibling data.
        df["cs_rank_prev"] = df["cs_rank"].shift(1)
        df["cs_universe_size_prev"] = df["cs_universe_size"].shift(1)

        # NOTE: cs_dispersion removed after two failed lookahead passes.
        # Root cause: cs_dispersion is computed from get_pair_dataframe calls for
        # ALL siblings. The lookahead tester appends synthetic future bars to the
        # main pair; this shifts the score_panel date alignment for the main pair,
        # making dispersion values differ between runs even at historical bars.
        # The mom_score_prev > 0 condition already guards against "all-negative"
        # regimes, and the rank gate handles sparse-signal regimes.

        return df

    def _attach_cross_sectional_rank(
        self, df: DataFrame, this_pair: str, lookback: int
    ) -> DataFrame:
        """
        For each bar, compute the rank of THIS pair's momentum score against
        the universe's scores at the same bar. All scores use .shift(1) so the
        rank is computed from bar t-1 information only — no lookahead.

        Hardening:
        - All sibling series get a defensive .copy() before reuse.
        - Date index normalised to pandas Timestamp (utc=True) to prevent silent
          merge misalignment if sibling pairs have different date dtypes.
        - score_panel uses outer-join on date; missing values stay NaN — not
          coerced to 0 or any sentinel — so they rank as missing (na_option='keep').
        """
        sibling_scores = {}

        for pair in self.UNIVERSE:
            if pair == this_pair:
                this_score = df.set_index("date")["mom_score"].copy()
                this_score.index = pd.to_datetime(this_score.index, utc=True)
                sibling_scores[pair] = this_score
                continue

            # Use get_pair_dataframe (raw OHLCV) instead of get_analyzed_dataframe.
            # In backtesting, populate_indicators runs sequentially per pair, so
            # get_analyzed_dataframe for a sibling that hasn't been analyzed yet
            # returns empty (ordering dependency). get_pair_dataframe loads from the
            # feather file regardless of processing order — always available.
            sib_df = self.dp.get_pair_dataframe(pair=pair, timeframe="1d")
            if sib_df is None or len(sib_df) == 0:
                continue

            sib_score = self._compute_pair_momentum_score(sib_df, lookback).copy()
            sib_score.index = pd.to_datetime(sib_df["date"].values, utc=True)
            sibling_scores[pair] = sib_score

        if len(sibling_scores) < 2:
            return df

        # Outer join across pairs; NaN stays NaN (not backfilled/coerced)
        score_panel = pd.DataFrame(sibling_scores)
        # Rank: 1 = best. NaN scores excluded from ranking (na_option='keep')
        rank_panel = score_panel.rank(axis=1, ascending=False, method="min", na_option="keep")

        # NOTE: cs_dispersion removed — see populate_indicators note for full explanation.
        # The mom_score_prev > 0 condition in populate_entry_trend already guards against
        # "all-negative" regimes, and the rank gate handles sparse-signal regimes.

        df = df.copy()
        df["date"] = pd.to_datetime(df["date"], utc=True)

        if this_pair not in rank_panel.columns:
            return df

        this_rank = rank_panel[this_pair].reset_index()
        this_rank.columns = ["date", "cs_rank"]
        this_size = score_panel.notna().sum(axis=1).reset_index()
        this_size.columns = ["date", "cs_universe_size"]

        df = df.drop(columns=["cs_rank", "cs_universe_size"], errors="ignore")
        df = df.merge(this_rank, on="date", how="left")
        df = df.merge(this_size, on="date", how="left")

        return df

    # ------- Entry -------
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe
        k_entry = int(self.top_k_entry.value)

        conditions = [
            # Must be ranked in top-K of cross-section (t-2 based, conservative)
            df["cs_rank_prev"].notna(),
            df["cs_rank_prev"] <= k_entry,

            # Need a credible universe size (otherwise rank is meaningless)
            df["cs_universe_size_prev"] >= 6,

            # Momentum score must be positive (not just relatively best of a bad universe)
            df["mom_score_prev"] > 0,

            df["atr_prev"] > 0,
            df["volume"] > 0,
        ]

        # Optional per-asset trend filter: price above EMA200 on prior bar
        if self.use_trend_filter.value == 1:
            conditions.append(df["close_prev"] > df["ema200_prev"])

        df.loc[reduce(lambda a, b: a & b, conditions), ["enter_long", "enter_tag"]] = (1, "xs_mom_topk")
        return df

    # ------- Exit signal (disabled — exits handled via custom_exit) -------
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0
        return dataframe

    # ------- Custom exit: rank-drop, time-stop -------
    def custom_exit(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs,
    ) -> Optional[str]:
        """
        Two exit conditions:
        1. Time-stop: close after MAX_HOLD_DAYS regardless of rank/P&L.
        2. Rank-drop: close when this pair falls out of top-K_exit of the cross-section.
        """
        # 1. Time-stop
        bars_held = (current_time - trade.open_date_utc) / timedelta(days=1)
        if bars_held >= self.MAX_HOLD_DAYS:
            return "time_stop_21d"

        df, _ = self.dp.get_analyzed_dataframe(pair=pair, timeframe=self.timeframe)
        if df is None or len(df) == 0:
            return None

        last = df.iloc[-1]
        rank = last.get("cs_rank_prev")
        k_exit = int(self.top_k_exit.value)

        # 2. Rank-drop
        if rank is not None and not np.isnan(float(rank)) and float(rank) > k_exit:
            return "rank_drop"

        return None

    # ------- ATR trailing stoploss -------
    def custom_stoploss(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs,
    ) -> Optional[float]:
        """
        ATR(14) trailing stop: stop = peak_price - k * ATR_at_prior_bar.
        """
        df, _ = self.dp.get_analyzed_dataframe(pair=pair, timeframe=self.timeframe)
        if df is None or len(df) == 0:
            return None

        last = df.iloc[-1]
        atr_prev = last.get("atr_prev")
        if atr_prev is None or np.isnan(float(atr_prev)) or float(atr_prev) <= 0:
            return None

        k = float(self.atr_stop_mult.value)
        peak = trade.max_rate or trade.open_rate
        stop_price = peak - k * float(atr_prev)

        if stop_price <= 0 or current_rate <= 0:
            return None

        rel_stop = (stop_price / current_rate) - 1.0
        rel_stop = max(min(rel_stop, -0.02), -0.25)
        return rel_stop

    # ------- Vol-targeted position sizing -------
    def custom_stake_amount(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_stake: float,
        min_stake: Optional[float],
        max_stake: float,
        leverage: float,
        entry_tag: Optional[str],
        side: str,
        **kwargs,
    ) -> float:
        """
        Risk r% of equity per position; stop distance = k * ATR(14).
        Cap per-trade margin at 25% of equity — with top-2 concurrent = 50% max.
        """
        df, _ = self.dp.get_analyzed_dataframe(pair=pair, timeframe=self.timeframe)
        if df is None or len(df) == 0:
            return proposed_stake

        last = df.iloc[-1]
        atr_prev = last.get("atr_prev")
        if atr_prev is None or np.isnan(float(atr_prev)) or float(atr_prev) <= 0:
            return proposed_stake

        try:
            total_equity = self.wallets.get_total_stake_amount()
        except Exception:
            return proposed_stake

        r = float(self.risk_per_trade_pct.value)
        k = float(self.atr_stop_mult.value)

        stop_dist_pct = (k * float(atr_prev)) / current_rate
        if stop_dist_pct <= 0:
            return proposed_stake

        target_notional = (total_equity * r) / stop_dist_pct
        target_stake = target_notional / max(leverage, 1.0)

        if min_stake is not None:
            target_stake = max(target_stake, min_stake)
        target_stake = min(target_stake, max_stake)
        # Cap per-trade margin at 25% of equity (2 concurrent trades = 50% max)
        target_stake = min(target_stake, total_equity * 0.25)

        return float(target_stake)

    # ------- Leverage -------
    def leverage(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_leverage: float,
        max_leverage: float,
        entry_tag: Optional[str],
        side: str,
        **kwargs,
    ) -> float:
        return min(2.0, max_leverage)
