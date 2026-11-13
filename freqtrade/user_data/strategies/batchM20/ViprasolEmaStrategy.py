# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
"""
ViprasolEmaStrategy
===================

A production-grade, fully hyperoptable Freqtrade strategy implementing a
trend-following EMA crossover that is filtered by RSI momentum, ADX trend
strength, Bollinger Band positioning, a volume surge, and a higher-timeframe
trend bias. Built and maintained by Viprasol Tech.

Logic
-----
Entry (long):
    * Fast EMA crosses above the slow EMA (a fresh uptrend), AND
    * RSI is above the oversold floor but below the overbought ceiling
      (momentum present but not exhausted), AND
    * ADX is above the trend-strength threshold (the trend is real, not chop), AND
    * Price is above the slow EMA (price confirms the trend), AND
    * Price is below the upper Bollinger Band (we are not chasing a blow-off top), AND
    * Volume on the candle exceeds its rolling mean by the surge factor
      (real participation, not an illiquid wick), AND
    * The higher-timeframe (4h) 200-EMA bias is bullish (optional, on by default).

Exit (long):
    * Fast EMA crosses back below the slow EMA (trend reversal), OR
    * RSI rises above the overbought ceiling (momentum exhausted), OR
    * Price closes above the upper Bollinger Band (over-extension / mean-revert risk).

Risk management:
    * Staged ``minimal_roi`` take-profit.
    * Hard ``stoploss`` floor.
    * Native trailing stop (locks profit once an offset is reached).
    * A custom, ATR-aware ``custom_stoploss`` that tightens the stop as a trade
      moves into profit.
    * Protections: ``CooldownPeriod``, ``MaxDrawdown``, ``StoplossGuard`` and
      ``LowProfitPairs`` to pause trading after adverse conditions.

Everything that matters is exposed as a hyperopt parameter (``IntParameter`` /
``DecimalParameter`` / ``BooleanParameter``) so the whole edge can be tuned with
``freqtrade hyperopt``.

DISCLAIMER
----------
This software is provided for educational and research purposes only. It is NOT
financial advice. Trading cryptocurrencies carries substantial risk. Past
performance does not guarantee future results. Use entirely at your own risk and
always backtest and dry-run before risking real capital.
"""

from __future__ import annotations

from datetime import datetime
from functools import reduce
from typing import Optional

from pandas import DataFrame

import talib.abstract as ta
from freqtrade.persistence import Trade
from freqtrade.strategy import (
    BooleanParameter,
    DecimalParameter,
    IntParameter,
    IStrategy,
    informative,
)
from freqtrade.strategy import qtpylib


class ViprasolEmaStrategy(IStrategy):
    """EMA crossover + RSI/ADX/Bollinger/volume filter trend strategy for Freqtrade."""

    # Strategy interface version - allow new iterations of the strategy interface.
    INTERFACE_VERSION = 3

    # Optimal timeframe for the strategy.
    timeframe = "1h"

    # Can this strategy go short?
    can_short: bool = False

    # Minimal ROI designed for the strategy (staged take-profit, in fractions).
    # Key = minutes since trade open, value = required profit fraction to exit.
    minimal_roi = {
        "0": 0.08,
        "60": 0.04,
        "180": 0.02,
        "360": 0.0,
    }

    # Optimal stoploss designed for the strategy (hard stop, negative fraction).
    stoploss = -0.10

    # Trailing stoploss configuration.
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.04
    trailing_only_offset_is_reached = True

    # Enable the ATR-aware custom stoploss callback below.
    use_custom_stoploss = True

    # Run "populate_indicators()" only for new candles (faster, deterministic).
    process_only_new_candles = True

    # These values can be overridden in the config.
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # Number of candles the strategy requires before producing valid signals.
    # The 4h 200-EMA informative is the binding constraint here.
    startup_candle_count: int = 200

    # ------------------------------------------------------------------ #
    # Hyperoptable parameters
    # ------------------------------------------------------------------ #
    # --- Entry (buy) space ---
    buy_rsi_floor = IntParameter(20, 45, default=30, space="buy", optimize=True)
    buy_rsi_ceiling = IntParameter(55, 75, default=70, space="buy", optimize=True)
    fast_ema_period = IntParameter(8, 21, default=12, space="buy", optimize=True)
    slow_ema_period = IntParameter(21, 60, default=26, space="buy", optimize=True)
    buy_adx_min = IntParameter(15, 40, default=25, space="buy", optimize=True)
    buy_volume_factor = DecimalParameter(
        1.0, 3.0, default=1.2, decimals=1, space="buy", optimize=True
    )
    buy_use_htf_trend = BooleanParameter(default=True, space="buy", optimize=True)

    # --- Exit (sell) space ---
    sell_rsi = IntParameter(70, 90, default=78, space="sell", optimize=True)
    sell_on_bb_upper = BooleanParameter(default=True, space="sell", optimize=True)

    # --- Protection space ---
    cooldown_lookback = IntParameter(2, 48, default=5, space="protection", optimize=True)
    stop_duration = IntParameter(12, 200, default=60, space="protection", optimize=True)
    use_stoploss_guard = BooleanParameter(
        default=True, space="protection", optimize=True
    )

    # --- Custom stoploss tuning (kept in the sell space) ---
    csl_atr_multiplier = DecimalParameter(
        1.0, 4.0, default=2.0, decimals=1, space="sell", optimize=True
    )

    # Bollinger Band configuration (fixed; well-understood defaults).
    bb_period: int = 20
    bb_std: float = 2.0

    # ------------------------------------------------------------------ #
    # Order handling
    # ------------------------------------------------------------------ #
    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }

    order_time_in_force = {
        "entry": "GTC",
        "exit": "GTC",
    }

    # ------------------------------------------------------------------ #
    # Plot configuration (freqtrade plot-dataframe)
    # ------------------------------------------------------------------ #
    plot_config = {
        "main_plot": {
            "ema_fast": {"color": "#1f77b4"},
            "ema_slow": {"color": "#ff7f0e"},
            "bb_upperband": {"color": "rgba(99,99,99,0.4)"},
            "bb_middleband": {"color": "rgba(99,99,99,0.6)"},
            "bb_lowerband": {"color": "rgba(99,99,99,0.4)"},
        },
        "subplots": {
            "RSI": {
                "rsi": {"color": "#9467bd"},
            },
            "ADX": {
                "adx": {"color": "#2ca02c"},
            },
            "Volume factor": {
                "volume_ratio": {"color": "#8c564b"},
            },
        },
    }

    # ------------------------------------------------------------------ #
    # Protections
    # ------------------------------------------------------------------ #
    @property
    def protections(self):
        prot = [
            {
                "method": "CooldownPeriod",
                "stop_duration_candles": int(self.cooldown_lookback.value),
            },
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 48,
                "trade_limit": 20,
                "stop_duration_candles": int(self.stop_duration.value),
                "max_allowed_drawdown": 0.20,
            },
            {
                "method": "LowProfitPairs",
                "lookback_period_candles": 24,
                "trade_limit": 4,
                "stop_duration_candles": int(self.stop_duration.value),
                "required_profit": 0.01,
            },
        ]
        if self.use_stoploss_guard.value:
            prot.append(
                {
                    "method": "StoplossGuard",
                    "lookback_period_candles": 24,
                    "trade_limit": 4,
                    "stop_duration_candles": int(self.stop_duration.value),
                    "only_per_pair": False,
                }
            )
        return prot

    # ------------------------------------------------------------------ #
    # Informative pairs (extra data fetched for the higher-timeframe bias)
    # ------------------------------------------------------------------ #
    def informative_pairs(self):
        """Explicitly request the 4h candles for every whitelisted pair.

        The ``@informative("4h")`` decorator already wires this up, but declaring
        it here keeps the dependency obvious and works even when the strategy is
        used in contexts where the decorator metadata is not introspected.
        """
        pairs = self.dp.current_whitelist()
        return [(pair, "4h") for pair in pairs]

    @informative("4h")
    def populate_indicators_4h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Higher-timeframe trend filter (200 EMA on the 4h chart)."""
        dataframe["ema_trend"] = ta.EMA(dataframe, timeperiod=200)
        dataframe["htf_bull"] = (dataframe["close"] > dataframe["ema_trend"]).astype(int)
        return dataframe

    # ------------------------------------------------------------------ #
    # Indicators
    # ------------------------------------------------------------------ #
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Add the technical indicators used by the entry/exit rules."""
        # Exponential moving averages (fast & slow).
        dataframe["ema_fast"] = ta.EMA(
            dataframe, timeperiod=int(self.fast_ema_period.value)
        )
        dataframe["ema_slow"] = ta.EMA(
            dataframe, timeperiod=int(self.slow_ema_period.value)
        )

        # Relative Strength Index momentum oscillator.
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        # Average Directional Index (trend strength, not direction).
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)
        dataframe["plus_di"] = ta.PLUS_DI(dataframe, timeperiod=14)
        dataframe["minus_di"] = ta.MINUS_DI(dataframe, timeperiod=14)

        # Average True Range (used by the custom stoploss).
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)

        # Bollinger Bands (volatility envelope around a typical-price SMA).
        bollinger = qtpylib.bollinger_bands(
            qtpylib.typical_price(dataframe),
            window=self.bb_period,
            stds=self.bb_std,
        )
        dataframe["bb_lowerband"] = bollinger["lower"]
        dataframe["bb_middleband"] = bollinger["mid"]
        dataframe["bb_upperband"] = bollinger["upper"]
        # Width as a fraction of price -> regime/volatility feature.
        dataframe["bb_width"] = (
            (dataframe["bb_upperband"] - dataframe["bb_lowerband"])
            / dataframe["bb_middleband"]
        )

        # Volume analysis: ratio of current volume to its rolling mean.
        dataframe["volume_mean"] = dataframe["volume"].rolling(window=20).mean()
        dataframe["volume_ratio"] = dataframe["volume"] / dataframe["volume_mean"]

        return dataframe

    # ------------------------------------------------------------------ #
    # Entry signal
    # ------------------------------------------------------------------ #
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Populate the entry (long) signal for the given DataFrame."""
        conditions = [
            # Fast EMA crosses above slow EMA -> fresh uptrend.
            qtpylib.crossed_above(dataframe["ema_fast"], dataframe["ema_slow"]),
            # Momentum present but not exhausted.
            dataframe["rsi"] > self.buy_rsi_floor.value,
            dataframe["rsi"] < self.buy_rsi_ceiling.value,
            # The trend is strong enough to be worth trading (not chop).
            dataframe["adx"] > self.buy_adx_min.value,
            # Directional movement agrees with a long.
            dataframe["plus_di"] > dataframe["minus_di"],
            # Price confirms the trend.
            dataframe["close"] > dataframe["ema_slow"],
            # Do not chase a blow-off top above the upper band.
            dataframe["close"] < dataframe["bb_upperband"],
            # Real participation: a volume surge above the rolling mean.
            dataframe["volume_ratio"] > self.buy_volume_factor.value,
            # Guard against trading on stale / illiquid candles.
            dataframe["volume"] > 0,
        ]

        # Optional higher-timeframe trend filter (column provided by @informative).
        if self.buy_use_htf_trend.value and "htf_bull_4h" in dataframe.columns:
            conditions.append(dataframe["htf_bull_4h"] == 1)

        dataframe.loc[reduce(lambda a, b: a & b, conditions), "enter_long"] = 1
        return dataframe

    # ------------------------------------------------------------------ #
    # Exit signal
    # ------------------------------------------------------------------ #
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Populate the exit (long) signal for the given DataFrame."""
        # Trend reversal OR momentum exhaustion always triggers an exit.
        exit_reason = (
            qtpylib.crossed_below(dataframe["ema_fast"], dataframe["ema_slow"])
            | (dataframe["rsi"] > self.sell_rsi.value)
        )

        # Optionally also exit on over-extension above the upper Bollinger Band.
        if self.sell_on_bb_upper.value:
            exit_reason = exit_reason | (
                dataframe["close"] > dataframe["bb_upperband"]
            )

        dataframe.loc[
            (exit_reason & (dataframe["volume"] > 0)),
            "exit_long",
        ] = 1
        return dataframe

    # ------------------------------------------------------------------ #
    # Custom (ATR-aware, profit-ratcheting) stoploss
    # ------------------------------------------------------------------ #
    def custom_stoploss(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        after_fill: bool,
        **kwargs,
    ) -> Optional[float]:
        """Tighten the stop as the trade moves into profit.

        While the trade is in loss or only marginally positive we leave the hard
        ``stoploss`` in place (return ``None``). Once it clears the first profit
        tier we move to an ATR-derived trailing distance and progressively
        tighten it as profit grows. The returned value is a *negative fraction*
        relative to ``current_rate``.
        """
        # Pull the latest analysed candle so we can read the ATR.
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe is None or len(dataframe) == 0:
            return None

        last_candle = dataframe.iloc[-1].squeeze()
        atr = last_candle.get("atr")

        # Default: keep the configured hard stop until we are in real profit.
        if current_profit < 0.02:
            return None

        # ATR-based distance, expressed as a fraction of the current rate.
        if atr is not None and current_rate > 0:
            atr_distance = (atr * float(self.csl_atr_multiplier.value)) / current_rate
        else:
            atr_distance = 0.04

        # Progressive ratchet: the deeper in profit, the tighter the stop.
        if current_profit > 0.10:
            desired = max(current_profit - 0.04, 0.05)
        elif current_profit > 0.05:
            desired = max(current_profit - 0.03, atr_distance)
        else:
            desired = atr_distance

        # Return as a negative fraction (stop below current price).
        return -abs(desired)

    # ------------------------------------------------------------------ #
    # Optional confirmation hook (extra liquidity guard before entering)
    # ------------------------------------------------------------------ #
    def confirm_trade_entry(
        self,
        pair: str,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        current_time: datetime,
        entry_tag: Optional[str],
        side: str,
        **kwargs,
    ) -> bool:
        """Final sanity check: refuse entries on a flat/zero-volume last candle."""
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe is None or len(dataframe) == 0:
            return False
        last_candle = dataframe.iloc[-1].squeeze()
        return bool(last_candle.get("volume", 0) > 0)
