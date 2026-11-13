"""H-009: 7-day breakout inside a 30d-over-90d uptrend, with a 3-day channel exit.

Closed candles only; channels the current candle is compared with are shifted
by one candle. Orders execute on the following candle. Spot long only.

Rules:
- Regime(t): SMA(720) > SMA(2160) and close > SMA(720).
- Entry: regime AND close > prior 168-bar high.
- Exit: close < prior 72-bar low OR close < SMA(720).
- 6% hard stop via stoploss; 24-candle cooldown after any exit.
- Exposure is not set here (sizing hooks are forbidden); it is
  tradable_balance_ratio in the backtest overlay and in the live config.
"""

from pandas import DataFrame
from freqtrade.strategy import IStrategy


class WeeklyBreakoutRegime_H009_v1(IStrategy):
    """Weekly channel breakout gated by a 30d/90d uptrend regime."""

    INTERFACE_VERSION = 3
    timeframe = "1h"
    can_short = False

    minimal_roi = {"0": 100.0}
    stoploss = -0.06
    startup_candle_count = 2400

    @property
    def protections(self):
        return [{"method": "CooldownPeriod", "stop_duration_candles": 24}]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["sma_fast"] = dataframe["close"].rolling(720).mean()
        dataframe["sma_slow"] = dataframe["close"].rolling(2160).mean()
        dataframe["entry_high"] = dataframe["high"].rolling(168).max().shift(1)
        dataframe["exit_low"] = dataframe["low"].rolling(72).min().shift(1)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                dataframe["sma_fast"].notna()
                & dataframe["sma_slow"].notna()
                & dataframe["entry_high"].notna()
                & (dataframe["sma_fast"] > dataframe["sma_slow"])
                & (dataframe["close"] > dataframe["sma_fast"])
                & (dataframe["close"] > dataframe["entry_high"])
                & (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"],
        ] = (1, "weekly_breakout168")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                dataframe["exit_low"].notna()
                & dataframe["sma_fast"].notna()
                & (
                    (dataframe["close"] < dataframe["exit_low"])
                    | (dataframe["close"] < dataframe["sma_fast"])
                )
                & (dataframe["volume"] > 0)
            ),
            ["exit_long", "exit_tag"],
        ] = (1, "low72_or_regime_lost")
        return dataframe
