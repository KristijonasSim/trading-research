# DonchianBTC1d.py
# Daily Donchian Channel Breakout for BTC/USDT futures.
# Migrated from 1h after IS regime analysis revealed timeframe mismatch
# with source paper (Distaso/Mele/Zarattini 2025).
#
# Changes from DonchianBTC1h:
#   1. timeframe = "1d" (matches paper's design horizon)
#   2. Direct period computation (no pre-compute grid)
#   3. ADX upper bound at 55 (filters overextended/blow-off entries)
#   4. EMA proximity cap at +10% (filters stretched late entries)
#   5. Minimum 5-bar hold via custom_exit (prevents premature channel exits)
#
# Bug fix vs user-supplied spec:
#   Donchian channels are shifted ONCE in populate_indicators (rolling.max().shift(1)),
#   then NOT included in the _prev shift loop. Entry/exit uses df["close"] (not
#   close_prev) against the already-lagged channel. This matches the 1h fix.
#   The original spec computed rolling.max() without shift, then shifted again in
#   the lookahead guard — producing close_prev > max(high[...includes high_prev])
#   which is always False.
#
# Freqtrade 2026.4 | OKX Futures USDT-M | isolated margin.

from datetime import datetime, timedelta
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


class DonchianBTC1d(IStrategy):
    """
    Long-only daily Donchian breakout on BTC/USDT, gated by EMA200 trend,
    ADX regime band (floor + ceiling), and EMA-proximity cap.
    ATR-based trailing stoploss, fractional-risk position sizing.
    """

    INTERFACE_VERSION = 3

    # ------- Core wiring -------
    timeframe = "1d"
    can_short: bool = False
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    startup_candle_count: int = 300  # EMA200 + 100-day channel + buffer

    # Hard backstop; primary stop is custom_stoploss
    stoploss = -0.25
    use_custom_stoploss = True

    # ROI disabled — primary exits are Donchian channel + ATR trailing stop.
    # NOTE: the original spec used keys 30/60/120, which Freqtrade interprets
    # as MINUTES (not days). For a daily strategy those would fire in 30 minutes.
    # Setting to 100x prevents ROI interference with multi-week trend rides.
    minimal_roi = {"0": 100.0}

    trailing_stop = False

    # ------- Hyperopt params (6 max) -------
    donchian_entry_period = IntParameter(20, 100, default=55, space="buy", optimize=True)
    donchian_exit_period = IntParameter(10, 55, default=20, space="sell", optimize=True)
    atr_stop_mult = DecimalParameter(2.0, 5.0, default=3.0, decimals=1, space="sell", optimize=True)
    adx_floor = IntParameter(15, 35, default=22, space="buy", optimize=True)
    # Range raised from 5-15% → 5-50%: on daily BTC a 10% cap blocks the entire
    # 2020-2021 bull run (BTC was 30-60% above EMA200). The 1h insight (10%+ entries
    # fail) does not translate to daily — on hourly it's a blow-off; on daily it's
    # a normal bull market. Hyperopt will find the right cap within 5-50%.
    ema_pct_max = DecimalParameter(5.0, 50.0, default=25.0, decimals=1, space="buy", optimize=True)
    risk_per_trade_pct = DecimalParameter(0.005, 0.015, default=0.01, decimals=3, space="buy", optimize=False)

    # Fixed — empirically derived from IS regime analysis of 1h version
    ADX_CEILING = 55
    MIN_HOLD_BARS = 5  # days; prevents immediate channel-touch exits

    # ------- Protections -------
    @property
    def protections(self):
        return [
            {"method": "CooldownPeriod", "stop_duration_candles": 2},
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 30,
                "trade_limit": 3,
                "stop_duration_candles": 7,
                "only_per_pair": False,
            },
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 180,  # ~6 months daily
                "trade_limit": 5,
                "stop_duration_candles": 14,
                "max_allowed_drawdown": 0.20,
            },
        ]

    # ------- Indicators -------
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()

        df["atr"] = ta.ATR(df, timeperiod=14)
        df["ema200"] = ta.EMA(df, timeperiod=200)
        df["adx"] = ta.ADX(df, timeperiod=14)

        # Donchian channels — rolling FIRST, then shift(1).
        # rolling(N).max() at bar t includes high[t], so shift(1) afterwards
        # yields max(high[t-N:t-1]) at bar t — the true prior-N-day high that
        # excludes the current bar. This matches the 1h strategy's correct fix.
        # These columns are NOT in shift_cols (already lagged here).
        entry_p = int(self.donchian_entry_period.value)
        exit_p = int(self.donchian_exit_period.value)
        df["donchian_high_entry"] = df["high"].rolling(entry_p).max().shift(1)
        df["donchian_low_exit"] = df["low"].rolling(exit_p).min().shift(1)

        # EMA proximity — distance above trend filter, as percentage
        df["ema_pct"] = (df["close"] / df["ema200"] - 1.0) * 100.0

        # Realized vol for sizing
        log_ret = np.log(df["close"] / df["close"].shift(1))
        df["realized_vol_30"] = log_ret.rolling(30).std()

        # --- LOOKAHEAD GUARD ---
        # Shift raw indicators by 1 so entry/exit logic reads bar t-1 values.
        # Donchian channels are NOT here — already lagged via .shift(1) above.
        shift_cols = [
            "atr", "ema200", "adx", "ema_pct", "realized_vol_30",
            "close", "high", "low",
        ]
        for col in shift_cols:
            df[f"{col}_prev"] = df[col].shift(1)

        return df

    # ------- Entry -------
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe

        conditions = [
            # Breakout: current close exceeds prior N-day high channel.
            # donchian_high_entry already holds max(high[t-N:t-1]) — no lookahead.
            df["close"] > df["donchian_high_entry"],

            # Trend filter: yesterday's close above yesterday's EMA200.
            df["close_prev"] > df["ema200_prev"],

            # ADX band: enough trend strength, but not blow-off exhaustion.
            df["adx_prev"] > self.adx_floor.value,
            df["adx_prev"] < self.ADX_CEILING,

            # EMA proximity cap: not chasing an already-extended move.
            df["ema_pct_prev"] < self.ema_pct_max.value,
            df["ema_pct_prev"] > 0,  # long side only (redundant with EMA filter; explicit)

            # Sanity
            df["atr_prev"] > 0,
            df["volume"] > 0,
        ]

        df.loc[
            reduce(lambda a, b: a & b, conditions),
            ["enter_long", "enter_tag"]
        ] = (1, "donch_brk_1d")
        return df

    # ------- Exit signal (disabled — exits handled via custom_exit + custom_stoploss) -------
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0
        return dataframe

    # ------- Custom exit with minimum hold period -------
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
        Donchian channel-break exit, gated by a minimum 5-day hold.
        Prevents small winners that exit on first channel touch from
        dragging down the W/L ratio (identified in 1h IS regime analysis).
        """
        bars_held = (current_time - trade.open_date_utc) / timedelta(days=1)
        if bars_held < self.MIN_HOLD_BARS:
            return None

        df, _ = self.dp.get_analyzed_dataframe(pair=pair, timeframe=self.timeframe)
        if df is None or len(df) == 0:
            return None

        last = df.iloc[-1]

        # donchian_low_exit is already shifted: holds min(low[t-N:t-1]) at bar t.
        # Compare current close against that prior-N-day low.
        dc_low = last.get("donchian_low_exit")
        close = last.get("close")

        if dc_low is None or close is None:
            return None
        if np.isnan(float(dc_low)) or np.isnan(float(close)):
            return None

        if float(close) < float(dc_low):
            return "donch_channel_exit"

        return None

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
        ATR(14) trailing stop: stop = max_price_seen - k * ATR_at_prior_bar.
        On daily bars, ATR(14) ≈ 2-week volatility window — appropriate scale.
        Returns the *relative* distance from current_rate (negative).
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
        # Daily bars: clamp between -2% (noise floor) and -25% (hard backstop).
        rel_stop = max(min(rel_stop, -0.02), -0.25)
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
        Fractional Kelly proxy: risk r% of equity, stop distance = k * ATR(14).
        notional_at_1x = (equity * r) / (k * ATR / price)
        stake (margin)  = notional / leverage
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
        Fixed 2x. Vol sizing targets risk; leverage unlocks the notional.
        2x keeps liquidation comfortably away from ATR stop.
        """
        return min(2.0, max_leverage)
