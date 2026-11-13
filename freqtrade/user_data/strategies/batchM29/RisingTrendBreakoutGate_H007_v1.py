"""H-007: 20-day breakout only inside a confirmed, rising multi-month uptrend.

Closed candles only; channels the current candle is compared with are shifted
by one candle. Orders execute on the following candle. Spot long only.

Rules:
- Regime(t): SMA(1200) > SMA(2400), SMA(2400)(t) > SMA(2400)(t-480),
  close > SMA(1200).
- Entry: regime AND close > prior 480-bar high.
- Exit: close < prior 240-bar low OR close < SMA(1200).
- 6% hard stop via stoploss; 120-candle cooldown after any exit.
"""

from pandas import DataFrame
from freqtrade.strategy import IStrategy


class RisingTrendBreakoutGate_H007_v1(IStrategy):
    """Breakout gated by a rising multi-month uptrend regime."""

    INTERFACE_VERSION = 3
    timeframe = "1h"
    can_short = False

    minimal_roi = {"0": 100.0}
    stoploss = -0.06
    startup_candle_count = 2880

    @property
    def protections(self):
        return [{"method": "CooldownPeriod", "stop_duration_candles": 120}]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["sma_fast"] = dataframe["close"].rolling(1200).mean()
        dataframe["sma_slow"] = dataframe["close"].rolling(2400).mean()
        dataframe["sma_slow_lag"] = dataframe["sma_slow"].shift(480)
        dataframe["entry_high"] = dataframe["high"].rolling(480).max().shift(1)
        dataframe["exit_low"] = dataframe["low"].rolling(240).min().shift(1)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                dataframe["sma_fast"].notna()
                & dataframe["sma_slow"].notna()
                & dataframe["sma_slow_lag"].notna()
                & dataframe["entry_high"].notna()
                & (dataframe["sma_fast"] > dataframe["sma_slow"])
                & (dataframe["sma_slow"] > dataframe["sma_slow_lag"])
                & (dataframe["close"] > dataframe["sma_fast"])
                & (dataframe["close"] > dataframe["entry_high"])
                & (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"],
        ] = (1, "gated_breakout480")
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
        ] = (1, "low240_or_regime_lost")
        return dataframe
