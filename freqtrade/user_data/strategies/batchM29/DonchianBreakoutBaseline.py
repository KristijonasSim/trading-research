"""Fixed-parameter Donchian breakout baseline for BTC/USDT spot.

This is an exploratory candidate, not a performance claim. The channel uses
only completed candles: today's signal compares the close with the prior
20-candle high/low, and orders are simulated on the following candle.

Rules:
- Entry: close breaks above the previous 20-candle high.
- Exit: close breaks below the previous 10-candle low, or stop-loss.
- Spot long only; no leverage, shorts, or machine learning.
"""

from pandas import DataFrame
from freqtrade.strategy import IStrategy


class DonchianBreakoutBaseline(IStrategy):
    """Interpretable fixed-parameter breakout candidate."""

    INTERFACE_VERSION = 3
    timeframe = "1h"
    can_short = False

    minimal_roi = {"0": 100.0}
    stoploss = -0.10
    startup_candle_count = 20

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Build channels from prior candles, excluding the current candle."""
        dataframe["donchian_high"] = dataframe["high"].rolling(20).max().shift(1)
        dataframe["donchian_low_exit"] = dataframe["low"].rolling(10).min().shift(1)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Enter after a close breaks the prior 20-candle high."""
        dataframe.loc[
            (
                (dataframe["close"] > dataframe["donchian_high"])
                & (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"],
        ] = (1, "donchian20_breakout")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Exit after a close breaks the prior 10-candle low."""
        dataframe.loc[
            (
                (dataframe["close"] < dataframe["donchian_low_exit"])
                & (dataframe["volume"] > 0)
            ),
            ["exit_long", "exit_tag"],
        ] = (1, "donchian10_breakdown")
        return dataframe
