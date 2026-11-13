# RiskManagedBetaOverlay.py
# Long-only BTC+ETH spot basket with SMA200 regime filter and vol-weighted sizing.
#
# Design:
#   Universe: BTC/USDT (spot) + ETH/USDT (spot) — Binance
#   Timeframe: 1d. max_open_trades: 2 (one position per basket leg).
#
#   Entry: close[t-1] > SMA200[t-1] AND SMA200 has been rising for 10+ bars.
#   Exit: close[t-1] < SMA200[t-1] OR SMA200 slope has turned negative.
#   Stop: 6 × ATR(14) trailing below peak close; clamped to [-0.25, -0.05].
#
#   Sizing: inverse-volatility (30d realized vol) weights across BTC+ETH legs.
#   When only one asset is above SMA200, that leg takes up to 100% of capital.
#   When both are below SMA200, strategy is flat (all cash).
#
#   NO hyperopt by design — off-the-shelf params, one locked backtest.
#   Acceptance gates are in benchmark_vs_voo.py (FROZEN — do not edit to pass).
#
# Anti-lookahead discipline:
#   All indicator comparisons in entry/exit use _prev suffix columns (shift 1).
#   custom_stoploss reads atr_prev (already shifted).
#   custom_stake_amount reads rvol_30_prev for sibling via get_pair_dataframe.
#
# Known limitations (per spec):
#   - Lags VOO badly in crypto winters (flat vs VOO +10%). Beats VOO over FULL
#     cycle, not every calendar year. That tradeoff is by design.
#   - First ~200 trading days have no SMA200 => no trades. Effective start ~2020-07.
#   - SMA200 exit is slow; 6x-ATR stop is the only backstop for flash crashes.
#   - Whipsaw near SMA200 in choppy regimes: slope-confirmation reduces but
#     does not eliminate false re-entries.
#   - BTC/ETH correlation → 1 in crashes; second leg adds no protection during
#     bear; the SMA200 flat-exit does the protecting.
#
# Freqtrade 2026.4 | Binance SPOT | USDT-quoted

from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy


class RiskManagedBetaOverlay(IStrategy):
    """
    Inverse-vol-weighted BTC+ETH basket with SMA200 regime gate.
    Off-the-shelf parameters. No hyperopt. One run, locked gates.
    """

    INTERFACE_VERSION = 3

    timeframe = "1d"
    can_short = False
    process_only_new_candles = True

    # SMA200 needs 200 bars; buffer for rolling-vol warmup.
    startup_candle_count: int = 250

    # Backstop stoploss; real stop is custom_stoploss (6x ATR).
    # Wide enough that custom_stoploss almost always fires first.
    stoploss = -0.25
    use_custom_stoploss = True

    # ROI disabled — exits via exit_signal or custom_stoploss only.
    minimal_roi = {"0": 100.0}
    trailing_stop = False
    use_exit_signal = True
    exit_profit_only = False

    # ---- Off-the-shelf parameters (DO NOT hyperopt) ----
    SMA_PERIOD        = 200   # regime filter: classic 200-day SMA
    SMA_SLOPE_BARS    = 10    # bars over which SMA200 must be rising (~2 weeks)
    ATR_PERIOD        = 14    # standard ATR for stop computation
    ATR_STOP_MULT     = 6.0   # stop = peak - 6 × ATR; wide, flash-crash backstop
    ATR_STOP_MIN      = 0.05  # clamp: minimum 5% distance (avoids noise exits)
    VOL_LOOKBACK      = 30    # 30d realized vol for inverse-vol position sizing

    UNIVERSE = ["BTC/USDT", "ETH/USDT"]

    # ---- Protections: minimal — strategy is long-only, regime-gated ----
    @property
    def protections(self):
        return [
            # Brief cooldown so the regime flip doesn't immediately re-enter
            {"method": "CooldownPeriod", "stop_duration_candles": 2},
        ]

    # ---- Informative pairs (spot only; no funding, no perp) ----
    def informative_pairs(self):
        return [("BTC/USDT", "1d"), ("ETH/USDT", "1d")]

    # ---- Indicators ----
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()

        # Trend
        df["sma200"] = ta.SMA(df, timeperiod=self.SMA_PERIOD)

        # SMA200 slope: compare today's SMA200 to N bars ago.
        # Positive → regime is trending up; negative → regime is decaying.
        # Both are computed from raw sma200 and then shifted below — no lookahead.
        df["sma200_slope"] = df["sma200"] - df["sma200"].shift(self.SMA_SLOPE_BARS)

        # Volatility / stop distance
        df["atr"] = ta.ATR(df, timeperiod=self.ATR_PERIOD)

        # Realized vol (30d log-return std) for inverse-vol weighting
        log_ret = np.log(df["close"] / df["close"].shift(1))
        df["rvol_30"] = log_ret.rolling(self.VOL_LOOKBACK).std()

        # ---- LOOKAHEAD GUARD ----
        # Shift ALL raw indicators by 1 so entry/exit logic at bar t reads
        # only information that was available at bar t-1 (close of prior bar).
        for col in ["sma200", "sma200_slope", "atr", "rvol_30", "close"]:
            df[f"{col}_prev"] = df[col].shift(1)

        return df

    # ---- Entry ----
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe

        # Both conditions must be true at bar t-1:
        # 1. Price closed above SMA200 (bull regime)
        # 2. SMA200 has been rising for at least SMA_SLOPE_BARS (anti-whipsaw)
        df.loc[
            (
                df["close_prev"].notna() &
                df["sma200_prev"].notna() &
                (df["close_prev"] > df["sma200_prev"]) &
                (df["sma200_slope_prev"] > 0) &
                (df["volume"] > 0)
            ),
            ["enter_long", "enter_tag"]
        ] = (1, "sma200_bull")

        return df

    # ---- Exit signal ----
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe

        # Exit when either condition was true at bar t-1:
        # 1. Price closed below SMA200 (regime broken)
        # 2. SMA200 slope turned negative (regime decaying)
        df.loc[
            (
                df["close_prev"].notna() &
                df["sma200_prev"].notna() &
                (
                    (df["close_prev"] < df["sma200_prev"]) |
                    (df["sma200_slope_prev"] <= 0)
                )
            ),
            "exit_long"
        ] = 1

        return df

    # ---- ATR trailing stoploss ----
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
        6 × ATR(14) trailing stop below the trade's peak close.
        Returns a relative stop value in (-1, 0).

        Clamped to [-0.25, -ATR_STOP_MIN]:
          - Lower bound matches static stoploss; stop can't be looser.
          - Upper bound prevents noise-triggered exits on wide-ATR bars.
        """
        df, _ = self.dp.get_analyzed_dataframe(pair=pair, timeframe=self.timeframe)
        if df is None or len(df) == 0:
            return None

        last = df.iloc[-1]
        atr_prev = last.get("atr_prev")
        if atr_prev is None or np.isnan(float(atr_prev)) or float(atr_prev) <= 0:
            return None

        peak = trade.max_rate or trade.open_rate
        stop_price = peak - self.ATR_STOP_MULT * float(atr_prev)

        if stop_price <= 0 or current_rate <= 0:
            return None

        rel_stop = (stop_price / current_rate) - 1.0
        rel_stop = max(min(rel_stop, -self.ATR_STOP_MIN), -0.25)
        return rel_stop

    # ---- Inverse-vol position sizing ----
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
        Each leg receives a fraction of total equity proportional to its
        inverse-volatility weight.

        w_this = (1/σ_this) / (1/σ_this + 1/σ_sib)

        Falls back to equal-weight (50%) if sibling data is unavailable.
        """
        df, _ = self.dp.get_analyzed_dataframe(pair=pair, timeframe=self.timeframe)
        if df is None or len(df) == 0:
            return proposed_stake

        last = df.iloc[-1]
        rvol_this = last.get("rvol_30_prev")

        # Sibling pair
        sib_pair = "ETH/USDT" if pair == "BTC/USDT" else "BTC/USDT"
        sib_df = self.dp.get_pair_dataframe(pair=sib_pair, timeframe=self.timeframe)

        if (
            sib_df is not None and len(sib_df) > 0 and
            rvol_this is not None and not np.isnan(float(rvol_this)) and float(rvol_this) > 0
        ):
            sib_log_ret = np.log(sib_df["close"] / sib_df["close"].shift(1))
            rvol_sib = sib_log_ret.rolling(self.VOL_LOOKBACK).std().iloc[-2]  # t-1 bar

            if (
                rvol_sib is not None and not np.isnan(float(rvol_sib)) and
                float(rvol_sib) > 0
            ):
                inv_this = 1.0 / float(rvol_this)
                inv_sib  = 1.0 / float(rvol_sib)
                w_this = inv_this / (inv_this + inv_sib)
            else:
                w_this = 0.5  # fallback: equal weight
        else:
            w_this = 0.5  # fallback: equal weight (no sibling data)

        try:
            total_equity = self.wallets.get_total_stake_amount()
        except Exception:
            return proposed_stake

        target_stake = total_equity * w_this

        # Clamp to Freqtrade's allowed range
        if min_stake is not None:
            target_stake = max(target_stake, min_stake)
        target_stake = min(target_stake, max_stake)

        return float(target_stake)

    # ---- No leverage (spot) ----
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
        return 1.0
