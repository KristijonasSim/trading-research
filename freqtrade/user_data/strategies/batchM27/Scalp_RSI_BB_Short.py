# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file

import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime, timedelta
from typing import Optional

from freqtrade.strategy import (
    IStrategy,
    Trade,
    Order,
    DecimalParameter,
    IntParameter,
    BooleanParameter,
)
from freqtrade.persistence import Trade as TradeModel

import talib.abstract as ta
from technical import qtpylib

import logging

logger = logging.getLogger(__name__)


class Scalp_RSI_BB_Short(IStrategy):
    """
    AI Crypto Scalping Agent - 5m Version with Advanced Risk Management

    Features:
    - Short-enabled RSI + Bollinger Bands
    - Volume + Trend filters
    - Dynamic position sizing
    - Protections (cooldown, max drawdown, stoploss guard)
    """

    INTERFACE_VERSION = 3

    timeframe = "5m"
    can_short = True

    minimal_roi = {
        "0": 0.012,
        "8": 0.008,
        "16": 0.004,
        "30": 0
    }

    stoploss = -0.012

    trailing_stop = True
    trailing_stop_positive = 0.004
    trailing_stop_positive_offset = 0.008
    trailing_only_offset_is_reached = True

    process_only_new_candles = True
    # EMA50 (and the BB window, up to 24) need enough history to converge;
    # 40 candles left the first ~10 candles of every run with bad signals.
    startup_candle_count = 100

    # === ADVANCED RISK MANAGEMENT ===
    # Position sizing: risk a fixed % of account per trade
    risk_per_trade = 0.01          # Risk 1% of account per trade
    # Hard cap in USDT (set None to disable). NOTE: the stake is the LESSER of
    # the risk-based size and this cap. With stoploss -1.2% the risk-based size
    # is ~83% of the balance, so on small accounts the cap is what binds and
    # the real risk per trade is cap * stoploss / balance (e.g. $100 * 1.2% /
    # $1000 = 0.12%), not risk_per_trade.
    max_stake_amount = 100
    fixed_leverage = 1.0           # Explicit; the sizing math below uses it

    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False
    }

    order_time_in_force = {
        "entry": "GTC",
        "exit": "GTC"
    }

    # Hyperopt parameters
    buy_rsi = IntParameter(22, 35, default=28, space="buy")
    sell_rsi = IntParameter(65, 80, default=72, space="sell")
    short_rsi = IntParameter(65, 80, default=72, space="sell")
    cover_rsi = IntParameter(22, 35, default=28, space="buy")

    bb_period = IntParameter(16, 24, default=20, space="buy")
    bb_std = DecimalParameter(1.8, 2.4, default=2.0, decimals=1, space="buy")
    volume_factor = DecimalParameter(0.6, 1.2, default=0.75, decimals=2, space="buy")

    # ---------- Protections (Advanced Risk Management) ----------
    @property
    def protections(self):
        return [
            {
                # Per-pair cooldown after a trade closes (prevents overtrading).
                # CooldownPeriod only takes a duration; there is no "CooldownRate".
                "method": "CooldownPeriod",
                "stop_duration_candles": 6
            },
            {
                # Stoploss guard - pause after consecutive losses
                "method": "StoplossGuard",
                "lookback_period_candles": 24,
                "trade_limit": 3,
                "stop_duration_candles": 12,
                "required_profit": 0.0,
                "only_per_pair": False,
                "only_per_side": False
            },
            {
                # Max drawdown protection
                "method": "MaxDrawdown",
                "lookback_period_candles": 48,
                "trade_limit": 10,
                "stop_duration_candles": 24,
                "max_allowed_drawdown": 0.08      # Pause if drawdown > 8%
            },
            {
                # Low profit pairs protection
                "method": "LowProfitPairs",
                "lookback_period_candles": 360,
                "trade_limit": 3,
                "stop_duration_candles": 60,
                "required_profit": 0.005,
                "only_per_pair": True
            }
        ]

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str],
                 side: str, **kwargs) -> float:
        """Fixed leverage so position sizing below is exact (futures only)."""
        return min(self.fixed_leverage, max_leverage)

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                            proposed_stake: float, min_stake: Optional[float], max_stake: float,
                            leverage: float, entry_tag: Optional[str], side: str,
                            **kwargs) -> float:
        """
        Dynamic position sizing based on risk percentage.
        Risks a fixed % of the TOTAL account balance per trade (so sizing does
        not shrink just because other trades are open).

        The stake is margin, and the loss at the stoploss is
        stake * leverage * |stoploss|, so
        stake = risk_amount / (|stoploss| * leverage).
        """
        try:
            balance = self.wallets.get_total(self.config["stake_currency"])
            risk_amount = balance * self.risk_per_trade

            stop_distance = abs(self.stoploss) * max(leverage, 1.0)
            if stop_distance > 0:
                stake = risk_amount / stop_distance
            else:
                stake = proposed_stake

            # Apply hard cap if set
            if self.max_stake_amount is not None:
                stake = min(stake, self.max_stake_amount)

            # Respect exchange min/max
            stake = max(min_stake or 0, stake)
            stake = min(stake, max_stake)

            return stake

        except Exception:
            # Never fall back to an uncapped stake: with stake_amount
            # "unlimited" the proposed stake can be a large share of the wallet.
            logger.exception("custom_stake_amount failed for %s; using capped fallback", pair)
            fallback = proposed_stake
            if self.max_stake_amount is not None:
                fallback = min(fallback, self.max_stake_amount)
            return fallback

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        bollinger = qtpylib.bollinger_bands(
            qtpylib.typical_price(dataframe),
            window=self.bb_period.value,
            stds=self.bb_std.value
        )
        dataframe["bb_lower"] = bollinger["lower"]
        dataframe["bb_middle"] = bollinger["mid"]
        dataframe["bb_upper"] = bollinger["upper"]

        dataframe["ema_50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema_20"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["volume_mean"] = dataframe["volume"].rolling(window=20).mean()

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # LONG
        dataframe.loc[
            (
                (dataframe["rsi"] < self.buy_rsi.value) &
                (dataframe["close"] <= dataframe["bb_lower"]) &
                (dataframe["volume"] > dataframe["volume_mean"] * self.volume_factor.value) &
                (dataframe["ema_20"] > dataframe["ema_50"]) &
                (dataframe["volume"] > 0)
            ),
            "enter_long"
        ] = 1

        # SHORT
        dataframe.loc[
            (
                (dataframe["rsi"] > self.short_rsi.value) &
                (dataframe["close"] >= dataframe["bb_upper"]) &
                (dataframe["volume"] > dataframe["volume_mean"] * self.volume_factor.value) &
                (dataframe["ema_20"] < dataframe["ema_50"]) &
                (dataframe["volume"] > 0)
            ),
            "enter_short"
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["rsi"] > self.sell_rsi.value) |
                (dataframe["close"] >= dataframe["bb_middle"])
            ),
            "exit_long"
        ] = 1

        dataframe.loc[
            (
                (dataframe["rsi"] < self.cover_rsi.value) |
                (dataframe["close"] <= dataframe["bb_middle"])
            ),
            "exit_short"
        ] = 1

        return dataframe
