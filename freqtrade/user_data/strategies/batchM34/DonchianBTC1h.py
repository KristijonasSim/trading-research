# DonchianBTC1h.py
# Donchian Channel Breakout Ensemble with ATR vol-targeted sizing.
# Reference: Distaso/Mele/Zarattini "Catching Crypto Trends" (SSRN 2025).
# Freqtrade 2026.4+ | Binance Futures USDT-M | isolated margin.

from datetime import datetime
from functools import reduce
from typing import Optional

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


class DonchianBTC1h(IStrategy):
    """
    Long-only Donchian breakout on BTC/USDT 1h, gated by EMA200 trend
    and ADX regime, with ATR-based custom stoploss and volatility-targeted
    fractional risk sizing.
    """

    INTERFACE_VERSION = 3

    # ------- Core wiring -------
    timeframe = "1h"
    can_short: bool = False  # post-halving regime: trend bias is up; shorts add noise
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    startup_candle_count: int = 750  # EMA200 (200) + max Donchian (500) + buffer

    # Static stoploss is a hard backstop; real stop is custom_stoploss (ATR).
    # -0.25 instead of -0.15: the ATR(100) × k stop for a 20-day trend entry
    # can legitimately be 15-20% wide in volatile BTC conditions; the -0.15
    # cap was clamping the stop and preventing winners from running.
    stoploss = -0.25
    use_custom_stoploss = True

    # ROI table disabled: primary exits are Donchian channel-break + ATR trailing stop.
    # Setting to 100x prevents interference with trend-riding.
    # Static stoploss=-15% and custom_stoploss remain the hard safety nets.
    minimal_roi = {"0": 100.0}

    # Trailing managed via custom_stoploss
    trailing_stop = False

    # ------- Hyperopt-exposed params (6 max) -------
    # Ranges extended for 1h BTC: 55 daily bars ≈ 1,320 1h bars.
    # 500-bar entry (≈21 days) is a reasonable mid-range for capturing
    # multi-week trends on hourly data.
    donchian_entry_period = IntParameter(50, 500, default=200, space="buy", optimize=True)
    donchian_exit_period = IntParameter(25, 200, default=100, space="sell", optimize=True)
    atr_stop_mult = DecimalParameter(3.0, 8.0, default=5.0, decimals=1, space="sell", optimize=True)
    adx_threshold = IntParameter(15, 35, default=20, space="buy", optimize=True)
    vol_zscore_min = DecimalParameter(-1.0, 2.0, default=0.0, decimals=2, space="buy", optimize=True)
    risk_per_trade_pct = DecimalParameter(0.005, 0.015, default=0.01, decimals=3, space="buy", optimize=False)

    # ------- Protections -------
    @property
    def protections(self):
        return [
            {"method": "CooldownPeriod", "stop_duration_candles": 4},
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 72,
                "trade_limit": 3,
                "stop_duration_candles": 24,
                "only_per_pair": False,
            },
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 720,  # ~30 days @ 1h
                "trade_limit": 10,
                "stop_duration_candles": 48,
                "max_allowed_drawdown": 0.15,
            },
        ]

    # ------- Indicators -------
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()

        # ATR(14) — kept for sizing reference.
        df["atr"] = ta.ATR(df, timeperiod=14)

        # ATR(100) — ~4-day volatility window used for the trailing stop.
        # Avoids the quiet-period collapse of ATR(14) that triggers stops
        # on normal 1-2% BTC noise.
        df["atr100"] = ta.ATR(df, timeperiod=100)

        # Trend filter
        df["ema200"] = ta.EMA(df, timeperiod=200)

        # Regime filter
        df["adx"] = ta.ADX(df, timeperiod=14)

        # Donchian channels — rolling FIRST, then shift(1).
        # rolling(N).max() at bar t includes high[t], so shift(1) afterwards
        # yields max(high[t-N:t-1]) at bar t — the true prior-N-bar high
        # that excludes the current bar.  This is the correct Turtle breakout:
        #   close[t] > donchian_high_N[t]  ==  close[t] > max(high[t-N:t-1])
        # These columns are NOT added to shift_cols (they are already lagged).
        # Step-25 grid: 25-500 covers both entry range (50-500) and exit range (25-200).
        for period in range(25, 501, 25):
            df[f"donchian_high_{period}"] = df["high"].rolling(period).max().shift(1)
            df[f"donchian_low_{period}"] = df["low"].rolling(period).min().shift(1)

        # Volume z-score (confirmation that breakout has participation)
        vol_ma = df["volume"].rolling(20).mean()
        vol_sd = df["volume"].rolling(20).std()
        df["vol_z"] = (df["volume"] - vol_ma) / vol_sd.replace(0, np.nan)

        # Realized vol over 30 bars (log returns), annualized-ish proxy for sizing
        log_ret = np.log(df["close"] / df["close"].shift(1))
        df["realized_vol_30"] = log_ret.rolling(30).std()

        # --- LOOKAHEAD GUARD ---
        # Raw indicator columns are shifted by 1 so entry/exit logic reads
        # bar t-1 data for filters.  Donchian channels are already lagged via
        # the .shift(1) applied above — do NOT shift them again here.
        shift_cols = (
            ["atr", "atr100", "ema200", "adx", "vol_z", "realized_vol_30", "close", "high", "low"]
        )
        for col in shift_cols:
            df[f"{col}_prev"] = df[col].shift(1)

        return df

    # ------- Entry -------
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe
        entry_p = self.donchian_entry_period.value
        # snap to nearest 25 (matches the pre-computed grid step)
        entry_p = int(round(entry_p / 25) * 25)
        entry_p = max(50, min(500, entry_p))
        # Ensure the period lands on the 25-step grid
        entry_p = (entry_p // 25) * 25 or 50  # floor to nearest 25, minimum 50

        # donchian_high_N is already shifted: at bar t it holds max(high[t-N:t-1])
        dc_high = df[f"donchian_high_{entry_p}"]

        conditions = [
            # Breakout: current close exceeds the prior N-bar high channel.
            # close[t] > max(high[t-N:t-1]) — no current-bar lookahead.
            df["close"] > dc_high,
            # Trend filter: price above EMA200 on bar t-1.
            df["close_prev"] > df["ema200_prev"],
            # Regime: trending, not chop.
            df["adx_prev"] > self.adx_threshold.value,
            # Participation: prior bar volume z-score elevated.
            df["vol_z_prev"] > self.vol_zscore_min.value,
            # Sanity: ATR exists.
            df["atr_prev"] > 0,
            # Volume sanity.
            df["volume"] > 0,
        ]

        df.loc[
            reduce(lambda a, b: a & b, conditions),
            ["enter_long", "enter_tag"]
        ] = (1, "donch_brk")
        return df

    # ------- Exit -------
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe
        exit_p = self.donchian_exit_period.value
        # snap to nearest 25 (matches the pre-computed grid step)
        exit_p = int(round(exit_p / 25) * 25)
        exit_p = max(25, min(200, exit_p))
        # Ensure the period lands on the 25-step grid
        exit_p = (exit_p // 25) * 25 or 25  # floor to nearest 25, minimum 25

        # donchian_low_N is already shifted: at bar t it holds min(low[t-N:t-1])
        dc_low = df[f"donchian_low_{exit_p}"]

        # Channel-break exit: current close below the prior N-bar low channel.
        df.loc[
            df["close"] < dc_low,
            ["exit_long", "exit_tag"]
        ] = (1, "donch_exit")
        return df

    # ------- ATR-based custom stoploss -------
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
        ATR(100) trailing stop: stop = max_price_seen - k * ATR100_at_prior_bar.
        ATR(100) ≈ 4-day volatility window — stable across quiet/volatile regimes.
        Returns the *relative* distance from current_rate (negative).
        """
        df, _ = self.dp.get_analyzed_dataframe(pair=pair, timeframe=self.timeframe)
        if df is None or len(df) == 0:
            return None

        last = df.iloc[-1]
        # Use ATR(100) for stop — avoids tight stops during low-volatility consolidation
        atr100_prev = last.get("atr100_prev")
        if atr100_prev is None or np.isnan(float(atr100_prev)) or float(atr100_prev) <= 0:
            # Fallback to ATR(14) if ATR(100) not available yet (warmup period)
            atr100_prev = last.get("atr_prev")
        if atr100_prev is None or np.isnan(float(atr100_prev)) or float(atr100_prev) <= 0:
            return None

        k = float(self.atr_stop_mult.value)
        # Highest price during trade approximated from trade.max_rate
        peak = trade.max_rate or trade.open_rate
        stop_price = peak - k * float(atr100_prev)

        if stop_price <= 0 or current_rate <= 0:
            return None

        rel_stop = (stop_price / current_rate) - 1.0
        # Clamp: never tighter than -1% or looser than -25%
        # (matching the class-level stoploss=-0.25 hard backstop)
        rel_stop = max(min(rel_stop, -0.01), -0.25)
        return rel_stop

    # ------- Volatility-targeted position sizing -------
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
        Fractional Kelly proxy: risk r% of equity, stop distance = k * ATR(100).
        notional_at_1x = (equity * r) / (k * ATR100 / price)
        stake (margin)  = notional / leverage
        Uses ATR(100) to match the stop width used in custom_stoploss.
        """
        df, _ = self.dp.get_analyzed_dataframe(pair=pair, timeframe=self.timeframe)
        if df is None or len(df) == 0:
            return proposed_stake

        last = df.iloc[-1]
        atr_prev = last.get("atr100_prev")
        if atr_prev is None or np.isnan(float(atr_prev)) or float(atr_prev) <= 0:
            atr_prev = last.get("atr_prev")  # fallback to ATR(14)
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

        # Notional position that risks r% of equity at the ATR stop
        target_notional = (total_equity * r) / stop_dist_pct
        target_stake = target_notional / max(leverage, 1.0)

        # Bound by engine limits
        if min_stake is not None:
            target_stake = max(target_stake, min_stake)
        target_stake = min(target_stake, max_stake)

        # Hard cap: never more than 50% of equity as margin on a single trade
        target_stake = min(target_stake, total_equity * 0.5)

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
        """
        Modest fixed leverage. Vol sizing already targets risk; leverage just
        unlocks the notional. 2x keeps liquidation comfortably away from ATR stop.
        """
        return min(2.0, max_leverage)
