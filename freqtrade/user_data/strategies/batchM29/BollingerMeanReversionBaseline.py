"""Fixed-parameter Bollinger mean-reversion candidate for BTC/USDT spot.

This is an exploratory candidate, not a performance claim. It intentionally
uses a regime filter because mean reversion can fail during persistent trends.

Rules:
- Entry: close is below the prior 20-candle lower Bollinger band, while close
  remains above SMA(200), and RSI(14) is below 30.
- Exit: close returns to the middle band, or stop-loss.
- Spot long only; no leverage, shorts, or machine learning.
"""

from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import IStrategy


class BollingerMeanReversionBaseline(IStrategy):
    """Interpretable fixed-parameter mean-reversion candidate."""

    INTERFACE_VERSION = 3
    timeframe = "1h"
    can_short = False

    minimal_roi = {"0": 100.0}
    stoploss = -0.10
    startup_candle_count = 200

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Calculate bands and regime indicators without future data."""
        basis = dataframe["close"].rolling(20).mean()
        deviation = dataframe["close"].rolling(20).std()
        dataframe["bb_middle"] = basis
        dataframe["bb_lower"] = basis - (2.0 * deviation)
        dataframe["sma_regime"] = ta.SMA(dataframe, timeperiod=200)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Enter an oversold excursion only above the long-term regime."""
        dataframe.loc[
            (
                (dataframe["close"] < dataframe["bb_lower"])
                & (dataframe["close"] > dataframe["sma_regime"])
                & (dataframe["rsi"] < 30)
                & (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"],
        ] = (1, "bb20_lower_rsi14_regime")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Exit when price returns to the middle Bollinger band."""
        dataframe.loc[
            (
                (dataframe["close"] > dataframe["bb_middle"])
                & (dataframe["volume"] > 0)
            ),
            ["exit_long", "exit_tag"],
        ] = (1, "bb20_mean_return")
        return dataframe
