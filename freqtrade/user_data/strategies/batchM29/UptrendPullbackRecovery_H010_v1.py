"""H-010: pullback recovery inside a 30d-over-100d uptrend, exit on the old high.

Closed candles only; every level the current candle is compared with is
shifted by one candle. Orders execute on the following candle. Spot long only.

Rules:
- Regime(t): close > SMA(2400) and SMA(720) > SMA(2400).
- Entry: regime AND min(close, t-48..t-1) <= 0.95 * max(high, t-336..t-1)
  AND close > SMA(48) AND previous close <= previous SMA(48).
- Exit: close >= max(high, t-336..t-1) (14-day high retested) OR close < SMA(2400).
- 5% hard stop via stoploss; 48-candle cooldown after any exit. No time stop.
- Exposure is not set here (sizing hooks are forbidden); it is
  tradable_balance_ratio in the backtest overlay and in the live config.
"""

from pandas import DataFrame
from freqtrade.strategy import IStrategy


class UptrendPullbackRecovery_H010_v1(IStrategy):
    """Buy the recovery of a 5% pullback while the 30d/100d uptrend holds."""

    INTERFACE_VERSION = 3
    timeframe = "1h"
    can_short = False

    minimal_roi = {"0": 100.0}
    stoploss = -0.05
    startup_candle_count = 2880

    @property
    def protections(self):
        return [{"method": "CooldownPeriod", "stop_duration_candles": 48}]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        close = dataframe["close"]
        dataframe["sma_long"] = close.rolling(2400).mean()
        dataframe["sma_mid"] = close.rolling(720).mean()
        dataframe["sma_fast"] = close.rolling(48).mean()
        dataframe["sma_fast_prev"] = dataframe["sma_fast"].shift(1)
        dataframe["close_prev"] = close.shift(1)
        dataframe["recent_low_close"] = close.rolling(48).min().shift(1)
        dataframe["prior_high"] = dataframe["high"].rolling(336).max().shift(1)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        valid = (
            dataframe["sma_long"].notna()
            & dataframe["sma_mid"].notna()
            & dataframe["sma_fast"].notna()
            & dataframe["sma_fast_prev"].notna()
            & dataframe["close_prev"].notna()
            & dataframe["recent_low_close"].notna()
            & dataframe["prior_high"].notna()
        )
        regime = (dataframe["close"] > dataframe["sma_long"]) & (
            dataframe["sma_mid"] > dataframe["sma_long"]
        )
        pullback = dataframe["recent_low_close"] <= 0.95 * dataframe["prior_high"]
        recovery = (dataframe["close"] > dataframe["sma_fast"]) & (
            dataframe["close_prev"] <= dataframe["sma_fast_prev"]
        )
        dataframe.loc[
            valid & regime & pullback & recovery & (dataframe["volume"] > 0),
            ["enter_long", "enter_tag"],
        ] = (1, "pullback_recovery")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                dataframe["prior_high"].notna()
                & dataframe["sma_long"].notna()
                & (
                    (dataframe["close"] >= dataframe["prior_high"])
                    | (dataframe["close"] < dataframe["sma_long"])
                )
                & (dataframe["volume"] > 0)
            ),
            ["exit_long", "exit_tag"],
        ] = (1, "high_retest_or_regime_lost")
        return dataframe
