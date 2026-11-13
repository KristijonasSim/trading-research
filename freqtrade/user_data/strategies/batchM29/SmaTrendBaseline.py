"""Baseline experimental strategy: SMA crossover for BTC/USDT spot.

This is an intentionally simple reference model, not an investment recommendation.
It is designed to validate the Freqtrade research workflow before any optimization.

Rules (evaluated on closed candles; orders are simulated on the next candle):
- Entry: SMA(20) crosses above SMA(50), with close above SMA(200).
- Exit: SMA(20) crosses below SMA(50), or a fixed stop-loss is reached.
- No shorting, leverage, futures, or machine learning.

The long SMA filter reduces entries against the broad trend, but can also delay
entries and miss recoveries. Parameters are fixed for the baseline experiment.
"""

from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import IStrategy


class SmaTrendBaseline(IStrategy):
    """Interpretable spot-only trend-following baseline."""

    INTERFACE_VERSION = 3
    timeframe = "1h"
    can_short = False

    # Fixed ex-ante for the reference run; do not optimize before validation.
    # Disable ROI exits for this baseline; exits are the SMA cross or stop-loss.
    minimal_roi = {"0": 100.0}
    stoploss = -0.10
    startup_candle_count = 200

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Calculate indicators using the current and prior candles only."""
        dataframe["sma_fast"] = ta.SMA(dataframe, timeperiod=20)
        dataframe["sma_slow"] = ta.SMA(dataframe, timeperiod=50)
        dataframe["sma_regime"] = ta.SMA(dataframe, timeperiod=200)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Enter when fast SMA crosses above slow SMA in the positive regime."""
        dataframe.loc[
            (
                (dataframe["sma_fast"] > dataframe["sma_slow"])
                & (dataframe["sma_fast"].shift(1) <= dataframe["sma_slow"].shift(1))
                & (dataframe["close"] > dataframe["sma_regime"])
                & (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"],
        ] = (1, "sma20_cross_up_regime")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Exit when fast SMA crosses below slow SMA."""
        dataframe.loc[
            (
                (dataframe["sma_fast"] < dataframe["sma_slow"])
                & (dataframe["sma_fast"].shift(1) >= dataframe["sma_slow"].shift(1))
                & (dataframe["volume"] > 0)
            ),
            ["exit_long", "exit_tag"],
        ] = (1, "sma20_cross_down")
        return dataframe
