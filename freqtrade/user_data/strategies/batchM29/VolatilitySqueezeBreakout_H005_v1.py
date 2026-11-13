"""H-005: long breakout after a multi-day volatility squeeze in an uptrend.

Closed candles only; every level the current candle is compared with is
shifted by one candle. Orders execute on the following candle. Spot long only.

Rules:
- R(t) = (highest high of 168 bars - lowest low of 168 bars) / close.
- Squeeze(t): R(t) <= rolling 0.20 quantile of R over the 2160 bars ending at t-1.
- Entry: squeeze true on at least one of the previous 24 bars AND
  close > prior 168-bar high AND close > SMA(2400) of close.
- Exit: close < prior 336-bar low; 8% hard stop via stoploss.
- Cooldown: 72 candles after any exit (CooldownPeriod protection).
"""

from pandas import DataFrame
from freqtrade.strategy import IStrategy


class VolatilitySqueezeBreakout_H005_v1(IStrategy):
    """Volatility squeeze breakout in an established uptrend."""

    INTERFACE_VERSION = 3
    timeframe = "1h"
    can_short = False

    minimal_roi = {"0": 100.0}
    stoploss = -0.08
    startup_candle_count = 2400

    @property
    def protections(self):
        return [{"method": "CooldownPeriod", "stop_duration_candles": 72}]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        range_high = dataframe["high"].rolling(168).max()
        range_low = dataframe["low"].rolling(168).min()
        dataframe["range_ratio"] = (range_high - range_low) / dataframe["close"]
        # Threshold excludes the current bar (shifted by one candle).
        dataframe["squeeze_threshold"] = (
            dataframe["range_ratio"].rolling(2160).quantile(0.20).shift(1)
        )
        valid = dataframe["range_ratio"].notna() & dataframe["squeeze_threshold"].notna()
        squeeze = (dataframe["range_ratio"] <= dataframe["squeeze_threshold"]).astype(float)
        squeeze = squeeze.where(valid)
        dataframe["squeeze"] = squeeze
        # Any squeeze on the previous 24 bars (t-24..t-1); NaN if any is undefined.
        dataframe["squeeze_recent"] = squeeze.shift(1).rolling(24).max()
        dataframe["entry_high"] = dataframe["high"].rolling(168).max().shift(1)
        dataframe["exit_low"] = dataframe["low"].rolling(336).min().shift(1)
        dataframe["trend_sma"] = dataframe["close"].rolling(2400).mean()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                dataframe["squeeze_recent"].notna()
                & dataframe["entry_high"].notna()
                & dataframe["trend_sma"].notna()
                & (dataframe["squeeze_recent"] >= 1)
                & (dataframe["close"] > dataframe["entry_high"])
                & (dataframe["close"] > dataframe["trend_sma"])
                & (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"],
        ] = (1, "squeeze_breakout")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                dataframe["exit_low"].notna()
                & (dataframe["close"] < dataframe["exit_low"])
                & (dataframe["volume"] > 0)
            ),
            ["exit_long", "exit_tag"],
        ] = (1, "low336_breakdown")
        return dataframe
