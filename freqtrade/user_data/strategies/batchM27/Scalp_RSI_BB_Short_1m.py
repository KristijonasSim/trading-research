# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file

import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from typing import Optional

from freqtrade.strategy import (
    IStrategy,
    Trade,
    Order,
    DecimalParameter,
    IntParameter,
    BooleanParameter,
)

import talib.abstract as ta
from technical import qtpylib

import logging

logger = logging.getLogger(__name__)


class Scalp_RSI_BB_Short_1m(IStrategy):
    """
    AI Crypto Scalping Agent - Aggressive 1m Version with Advanced Risk Management
    """

    INTERFACE_VERSION = 3

    timeframe = "1m"
    can_short = True

    minimal_roi = {
        "0": 0.008,
        "3": 0.005,
        "6": 0.003,
        "12": 0
    }

    stoploss = -0.008

    trailing_stop = True
    trailing_stop_positive = 0.003
    trailing_stop_positive_offset = 0.005
    trailing_only_offset_is_reached = True

    process_only_new_candles = True
    startup_candle_count = 40

    # === ADVANCED RISK MANAGEMENT ===
    risk_per_trade = 0.008         # Slightly lower risk on 1m (0.8%)
    # Hard cap in USDT. The stake is the LESSER of the risk-based size and this
    # cap. With stoploss -0.8% the risk-based size equals the whole balance, so
    # the cap is what binds above ~$64 and the real risk per trade is
    # cap * stoploss / balance (e.g. $80 * 0.8% / $1000 = 0.064%).
    max_stake_amount = 80
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

    buy_rsi = IntParameter(18, 32, default=25, space="buy")
    sell_rsi = IntParameter(68, 82, default=75, space="sell")
    short_rsi = IntParameter(68, 82, default=75, space="sell")
    cover_rsi = IntParameter(18, 32, default=25, space="buy")

    bb_period = IntParameter(12, 20, default=14, space="buy")
    bb_std = DecimalParameter(1.6, 2.2, default=1.9, decimals=1, space="buy")
    volume_factor = DecimalParameter(0.5, 1.1, default=0.7, decimals=2, space="buy")

    @property
    def protections(self):
        return [
            {
                # Per-pair cooldown after a trade closes. CooldownPeriod only
                # takes a duration; there is no "CooldownRate".
                "method": "CooldownPeriod",
                "stop_duration_candles": 10
            },
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 30,
                "trade_limit": 4,
                "stop_duration_candles": 20,
                "required_profit": 0.0,
                "only_per_pair": False,
                "only_per_side": False
            },
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 60,
                "trade_limit": 12,
                "stop_duration_candles": 30,
                "max_allowed_drawdown": 0.06
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
        Risk a fixed % of the TOTAL balance per trade. The stake is margin and
        the loss at the stoploss is stake * leverage * |stoploss|, so
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

            if self.max_stake_amount is not None:
                stake = min(stake, self.max_stake_amount)

            stake = max(min_stake or 0, stake)
            stake = min(stake, max_stake)
            return stake
        except Exception:
            # Never fall back to an uncapped stake (stake_amount is "unlimited").
            logger.exception("custom_stake_amount failed for %s; using capped fallback", pair)
            fallback = proposed_stake
            if self.max_stake_amount is not None:
                fallback = min(fallback, self.max_stake_amount)
            return fallback

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=10)

        bollinger = qtpylib.bollinger_bands(
            qtpylib.typical_price(dataframe),
            window=self.bb_period.value,
            stds=self.bb_std.value
        )
        dataframe["bb_lower"] = bollinger["lower"]
        dataframe["bb_middle"] = bollinger["mid"]
        dataframe["bb_upper"] = bollinger["upper"]

        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=9)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=21)
        dataframe["volume_mean"] = dataframe["volume"].rolling(window=15).mean()

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["rsi"] < self.buy_rsi.value) &
                (dataframe["close"] <= dataframe["bb_lower"]) &
                (dataframe["volume"] > dataframe["volume_mean"] * self.volume_factor.value) &
                (dataframe["ema_fast"] > dataframe["ema_slow"]) &
                (dataframe["volume"] > 0)
            ),
            "enter_long"
        ] = 1

        dataframe.loc[
            (
                (dataframe["rsi"] > self.short_rsi.value) &
                (dataframe["close"] >= dataframe["bb_upper"]) &
                (dataframe["volume"] > dataframe["volume_mean"] * self.volume_factor.value) &
                (dataframe["ema_fast"] < dataframe["ema_slow"]) &
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
