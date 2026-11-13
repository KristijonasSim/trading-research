# RegimeFilteredMomentum.py
# Short-term time-series momentum with BTC regime filter.
# Original design: "RegimeFilteredShortTermMomentum" (user-supplied).
# Literature: short-term crypto momentum + volatility regime management.
#
# Universe: top liquid USDT-M futures on OKX (static whitelist).
# Timeframe: 1h. Long-only (no shorting). max_open_trades: 5.
# Edge: ride short-term winners in confirmed trends + favorable market regime.
# Exits: trend break, regime turn, RSI overbought, ROI tiers, trailing stop.
#
# Changes from user-supplied spec:
#   1. pandas_ta → talib.abstract (confirmed installed in this environment).
#   2. Informative pair: BTC/USDT:USDT (futures) instead of BTC/USDT (spot) —
#      consistent with futures config; OKX spot BTC data has gaps pre-2022.
#   3. BTC regime columns shifted by 1 after merge (anti-lookahead discipline).
#   4. roc_24 computed directly (talib ROC already returns %, no * 100 needed).
#   5. ROI table kept as-is: keys are in MINUTES, increasing threshold over time
#      (small wins taken early, runners held for larger moves).
#   6. use_custom_stoploss = False (using static stoploss + trailing stop instead).
#   7. startup_candle_count raised to 250 (covers EMA200 + ATR14 warmup + buffer).
#
# Freqtrade 2026.4 | OKX Futures USDT-M | isolated margin.

from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IStrategy, merge_informative_pair


class RegimeFilteredMomentum(IStrategy):
    """
    Short-term momentum strategy with multi-confirmation entry and BTC regime gate.
    Designed for a diversified portfolio of liquid futures pairs.
    """

    INTERFACE_VERSION = 3

    timeframe = "1h"
    startup_candle_count: int = 250

    # Hard stop
    stoploss = -0.08
    use_custom_stoploss = False

    # ROI tiers (keys = MINUTES; increasing target lets runners breathe):
    # 0–120 min: take 2%+ profits quickly
    # 2h–6h: wait for 4%+ before exiting
    # 6h–12h: wait for 6%+
    # 12h+: wait for 8%+ (trend has confirmed itself; hold for full move)
    minimal_roi = {
        "0": 0.02,
        "120": 0.04,
        "360": 0.06,
        "720": 0.08,
    }

    # Trailing stop: activate once 3% profit reached, trail at 2%
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True

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
        ]

    # ------- Informative pairs -------
    def informative_pairs(self):
        return [("BTC/USDT:USDT", "1h")]

    # ------- Indicators -------
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # --- Per-pair trend/momentum indicators ---
        dataframe["ema_12"]  = ta.EMA(dataframe, timeperiod=12)
        dataframe["ema_26"]  = ta.EMA(dataframe, timeperiod=26)
        dataframe["ema_50"]  = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema_200"] = ta.EMA(dataframe, timeperiod=200)

        dataframe["adx"]     = ta.ADX(dataframe, timeperiod=14)
        dataframe["atr"]     = ta.ATR(dataframe, timeperiod=14)
        dataframe["rsi"]     = ta.RSI(dataframe, timeperiod=14)

        # ROC(24) = 24h return in % — talib already returns %, no extra *100
        dataframe["roc_24"]  = ta.ROC(dataframe, timeperiod=24)

        # Volume filter: is current bar's volume above 20-bar average?
        dataframe["volume_sma"] = dataframe["volume"].rolling(20).mean()

        # Realized vol (24h log-return std) for optional vol filter
        log_ret = np.log(dataframe["close"] / dataframe["close"].shift(1))
        dataframe["realized_vol_24"] = log_ret.rolling(24).std() * 100

        # --- BTC regime (informative 1h) ---
        btc_df = self.dp.get_pair_dataframe(pair="BTC/USDT:USDT", timeframe=self.timeframe)
        if btc_df is not None and len(btc_df) > 0:
            btc_df = btc_df.copy()
            btc_df["btc_ema200"] = ta.EMA(btc_df, timeperiod=200)

            # Merge on date (same timeframe — direct timestamp alignment)
            btc_slim = btc_df[["date", "close", "btc_ema200"]].rename(
                columns={"close": "btc_close", "btc_ema200": "btc_ema200"}
            )
            dataframe = dataframe.merge(btc_slim, on="date", how="left")

            # Shift BTC columns by 1 bar — anti-lookahead discipline.
            # Regime filter at bar t uses BTC's bar t-1 state.
            dataframe["btc_close_prev"]  = dataframe["btc_close"].shift(1)
            dataframe["btc_ema200_prev"] = dataframe["btc_ema200"].shift(1)
        else:
            # No BTC data available — default to neutral (no regime gate)
            dataframe["btc_close_prev"]  = np.nan
            dataframe["btc_ema200_prev"] = np.nan

        return dataframe

    # ------- Entry -------
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        btc_ok = (
            dataframe["btc_close_prev"].notna() &
            (dataframe["btc_close_prev"] > dataframe["btc_ema200_prev"])
        )

        dataframe.loc[
            (
                # 24h return > 1.5% (positive short-term momentum)
                (dataframe["roc_24"] > 1.5) &
                # Price above fast EMA (short-term uptrend)
                (dataframe["close"] > dataframe["ema_12"]) &
                # Fast EMA above slow EMA (trend confirmed)
                (dataframe["ema_12"] > dataframe["ema_26"]) &
                # Trend strength: not choppy
                (dataframe["adx"] > 25) &
                # Volume confirmation
                (dataframe["volume"] > dataframe["volume_sma"] * 1.2) &
                # Not overbought
                (dataframe["rsi"] < 75) &
                # Market regime: BTC in bull
                btc_ok &
                # Sanity
                (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"]
        ] = (1, "mom_regime_bull")

        return dataframe

    # ------- Exit -------
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # Price breaks below fast EMA (short-term trend broken)
                (dataframe["close"] < dataframe["ema_12"]) |
                # ADX weakening AND price below 26 EMA (trend fading)
                ((dataframe["adx"] < 20) & (dataframe["close"] < dataframe["ema_26"])) |
                # RSI extreme overbought
                (dataframe["rsi"] > 80) |
                # Regime turns bearish
                (
                    dataframe["btc_close_prev"].notna() &
                    (dataframe["btc_close_prev"] < dataframe["btc_ema200_prev"])
                )
            ),
            "exit_long"
        ] = 1

        return dataframe

    # ------- Leverage (spot equivalent) -------
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
        # 1x only — strategy designed as "spot equivalent" even on futures
        return 1.0
