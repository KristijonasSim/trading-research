from __future__ import annotations

import math
from datetime import datetime

import numpy as np
import pandas as pd
from pandas import DataFrame, Series

from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy, merge_informative_pair


class EthMtfBalancedMomentum(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "15m"
    can_short = True
    process_only_new_candles = True
    startup_candle_count = 600

    minimal_roi = {"0": 100.0}
    stoploss = -0.30
    trailing_stop = False
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    order_types = {
        "entry": "market",
        "exit": "market",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }
    order_time_in_force = {"entry": "GTC", "exit": "GTC"}

    leverage_value = 3.0
    ch_stake_fraction = 0.25
    hma_stake_fraction = 0.50

    ch_hold_minutes = 72 * 15
    ch_raw_take = 0.014
    ch_raw_stop = -0.014

    hma_hold_minutes = 48 * 15
    hma_raw_stop = -0.06
    hma_raw_trail = 0.10

    atr_min = 0.0012
    atr_max = 0.045

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        return [(pair, timeframe) for pair in pairs for timeframe in ("1h", "4h")]

    @staticmethod
    def _ema(series: Series, span: int) -> Series:
        return series.ewm(span=span, adjust=False, min_periods=span).mean()

    @staticmethod
    def _rsi(series: Series, period: int) -> Series:
        delta = series.diff()
        gain = delta.clip(lower=0.0).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        loss = (-delta.clip(upper=0.0)).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        return 100.0 - 100.0 / (1.0 + gain / loss)

    @staticmethod
    def _atr(dataframe: DataFrame, period: int) -> Series:
        previous_close = dataframe["close"].shift(1)
        true_range = pd.concat(
            [
                dataframe["high"] - dataframe["low"],
                (dataframe["high"] - previous_close).abs(),
                (dataframe["low"] - previous_close).abs(),
            ],
            axis=1,
        ).max(axis=1)
        return true_range.rolling(period, min_periods=period).mean()

    @staticmethod
    def _wma(series: Series, length: int) -> Series:
        weights = np.arange(1, length + 1, dtype=float)
        total = weights.sum()
        return series.rolling(length, min_periods=length).apply(
            lambda values: float(np.dot(values, weights) / total),
            raw=True,
        )

    def _hma(self, series: Series, length: int) -> Series:
        return self._wma(
            2.0 * self._wma(series, max(1, length // 2)) - self._wma(series, length),
            max(1, int(math.sqrt(length))),
        )

    @staticmethod
    def _linreg(series: Series, length: int) -> Series:
        x = np.arange(length, dtype=float)
        x_mean = x.mean()
        denom = ((x - x_mean) ** 2).sum()
        target_x = float(length - 1)

        def calc(values: np.ndarray) -> float:
            if not np.isfinite(values).all():
                return np.nan
            y_mean = values.mean()
            slope = ((x - x_mean) * (values - y_mean)).sum() / denom
            return y_mean - slope * x_mean + slope * target_x

        return series.rolling(length, min_periods=length).apply(calc, raw=True)

    def _add_trend_indicators(self, dataframe: DataFrame, fast: int, slow: int) -> DataFrame:
        result = dataframe.copy()
        fast_ema = self._ema(result["close"], fast)
        slow_ema = self._ema(result["close"], slow)
        result["trend"] = 0
        result.loc[fast_ema > slow_ema, "trend"] = 1
        result.loc[fast_ema < slow_ema, "trend"] = -1
        result["trend_strength"] = (fast_ema - slow_ema).abs() / result["close"]
        result["trend_slope"] = slow_ema.pct_change(6)
        result["trend_rsi"] = self._rsi(result["close"], 14)
        return result

    def _add_base_indicators(self, dataframe: DataFrame) -> DataFrame:
        dataframe["atr"] = self._atr(dataframe, 14)
        dataframe["atr_pct"] = dataframe["atr"] / dataframe["close"]

        channel_high = dataframe["high"].shift(1).rolling(48, min_periods=48).max()
        channel_low = dataframe["low"].shift(1).rolling(48, min_periods=48).min()
        dataframe["pos48"] = (dataframe["close"] - channel_low) / (channel_high - channel_low)

        hma = self._hma(dataframe["close"], 144)
        rising = hma > hma.shift(1).rolling(3, min_periods=3).max()
        falling = hma < hma.shift(1).rolling(3, min_periods=3).min()

        states: list[int] = []
        current = 0
        for is_rising, is_falling in zip(rising.fillna(False), falling.fillna(False)):
            if is_rising:
                current = 1
            elif is_falling:
                current = -1
            states.append(current)
        hma_state = pd.Series(states, index=dataframe.index)
        dataframe["hma_up_cross"] = hma_state.eq(1) & hma_state.shift(1).eq(-1)
        dataframe["hma_down_cross"] = hma_state.eq(-1) & hma_state.shift(1).eq(1)

        mean = dataframe["close"].rolling(48, min_periods=48).mean()
        high = dataframe["high"].rolling(48, min_periods=48).max()
        low = dataframe["low"].rolling(48, min_periods=48).min()
        squeeze_source = dataframe["close"] - (((high + low) / 2.0 + mean) / 2.0)
        dataframe["sqz_val"] = self._linreg(squeeze_source, 48)
        dataframe["sqz_norm"] = dataframe["sqz_val"] / dataframe["atr"]
        dataframe["sqz_slope"] = dataframe["sqz_val"].diff()
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair = metadata["pair"]
        dataframe = self._add_base_indicators(dataframe)

        inf_1h = self._add_trend_indicators(self.dp.get_pair_dataframe(pair=pair, timeframe="1h"), 20, 50)
        dataframe = merge_informative_pair(
            dataframe,
            inf_1h[["date", "trend", "trend_strength", "trend_slope", "trend_rsi"]],
            self.timeframe,
            "1h",
            ffill=True,
        )

        inf_4h = self._add_trend_indicators(self.dp.get_pair_dataframe(pair=pair, timeframe="4h"), 50, 200)
        dataframe = merge_informative_pair(
            dataframe,
            inf_4h[["date", "trend", "trend_strength", "trend_slope", "trend_rsi"]],
            self.timeframe,
            "4h",
            ffill=True,
        )
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        tradable = (
            (dataframe["volume"] > 0)
            & dataframe["atr_pct"].between(self.atr_min, self.atr_max)
        )
        channel_long = (
            tradable
            & (dataframe["trend_1h"] > 0)
            & (dataframe["trend_slope_1h"] > -0.004)
            & (dataframe["trend_strength_4h"] > 0.006)
            & (dataframe["trend_strength_4h"] < 0.060)
            & (dataframe["pos48"] > 0.82)
            & (dataframe["pos48"].shift(1) <= 0.82)
        )
        hma_short = (
            tradable
            & dataframe["hma_down_cross"]
            & (dataframe["sqz_norm"] < 0)
            & (dataframe["sqz_slope"] < 0)
            & (dataframe["trend_slope_1h"] < 0.006)
            & (dataframe["trend_slope_4h"] < 0.012)
        )

        dataframe.loc[channel_long, ["enter_long", "enter_tag"]] = (1, "ch48_long")
        dataframe.loc[hma_short, ["enter_short", "enter_tag"]] = (1, "hma_short")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["hma_up_cross"], ["exit_short", "exit_tag"]] = (1, "hma_up_cross")
        return dataframe

    @staticmethod
    def _is_channel_tag(entry_tag: str | None) -> bool:
        return entry_tag == "ch48_long"

    @staticmethod
    def _is_hma_tag(entry_tag: str | None) -> bool:
        return entry_tag == "hma_short"

    @staticmethod
    def _raw_profit(trade: Trade, current_rate: float) -> float:
        if trade.is_short:
            return trade.open_rate / current_rate - 1.0
        return current_rate / trade.open_rate - 1.0

    def custom_exit(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs,
    ) -> str | bool | None:
        hold_minutes = (current_time - trade.open_date_utc).total_seconds() / 60.0
        raw_profit = self._raw_profit(trade, current_rate)

        if self._is_channel_tag(trade.enter_tag):
            if raw_profit >= self.ch_raw_take:
                return "ch_take"
            if raw_profit <= self.ch_raw_stop:
                return "ch_stop"
            if hold_minutes >= self.ch_hold_minutes:
                return "ch_time"
            return None

        if self._is_hma_tag(trade.enter_tag):
            if raw_profit <= self.hma_raw_stop:
                return "hma_stop"

            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            if not dataframe.empty:
                since_entry = dataframe[dataframe["date"] >= trade.open_date_utc]
                if not since_entry.empty:
                    best_raw_profit = (trade.open_rate / since_entry["close"].min()) - 1.0
                    if best_raw_profit - raw_profit >= self.hma_raw_trail:
                        return "hma_trail"

            if hold_minutes >= self.hma_hold_minutes:
                return "hma_time"
        return None

    def custom_stake_amount(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_stake: float,
        min_stake: float | None,
        max_stake: float,
        leverage: float,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> float:
        if self._is_channel_tag(entry_tag):
            return min(proposed_stake * self.ch_stake_fraction, max_stake)
        if self._is_hma_tag(entry_tag):
            return min(proposed_stake * self.hma_stake_fraction, max_stake)
        return proposed_stake

    def leverage(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_leverage: float,
        max_leverage: float,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> float:
        return min(self.leverage_value, max_leverage)
