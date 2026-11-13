"""H-017: H-009 weekly breakout plus a rising 90-day mean condition.

Closed candles only; channels the current candle is compared with are shifted
by one candle. Orders execute on the following candle. Spot long only.

Rules:
- Regime(t): SMA(720) > SMA(2160) AND close > SMA(720)
  AND SMA(2160)(t) > SMA(2160)(t-720).
- Entry: regime AND close > prior 168-bar high.
- Exit: close < prior 72-bar low OR close < SMA(720).
- 6% hard stop via stoploss; 24-candle cooldown after any exit.
- Exposure is not set here; it is tradable_balance_ratio in the overlay.
"""

from pandas import DataFrame
from freqtrade.strategy import IStrategy


class WeeklyBreakoutRegime_H017_v1(IStrategy):
    """Weekly channel breakout gated by a rising 30d/90d uptrend regime."""

    INTERFACE_VERSION = 3
    timeframe = "1h"
    can_short = False

    minimal_roi = {"0": 100.0}
    stoploss = -0.06
    startup_candle_count = 2880

    @property
    def protections(self):
        return [{"method": "CooldownPeriod", "stop_duration_candles": 24}]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["sma_fast"] = dataframe["close"].rolling(720).mean()
        dataframe["sma_slow"] = dataframe["close"].rolling(2160).mean()
        dataframe["sma_slow_lag"] = dataframe["sma_slow"].shift(720)
        dataframe["entry_high"] = dataframe["high"].rolling(168).max().shift(1)
        dataframe["exit_low"] = dataframe["low"].rolling(72).min().shift(1)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                dataframe["sma_fast"].notna()
                & dataframe["sma_slow"].notna()
                & dataframe["sma_slow_lag"].notna()
                & dataframe["entry_high"].notna()
                & (dataframe["sma_fast"] > dataframe["sma_slow"])
                & (dataframe["close"] > dataframe["sma_fast"])
                & (dataframe["sma_slow"] > dataframe["sma_slow_lag"])
                & (dataframe["close"] > dataframe["entry_high"])
                & (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"],
        ] = (1, "weekly_breakout168_rising")
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
