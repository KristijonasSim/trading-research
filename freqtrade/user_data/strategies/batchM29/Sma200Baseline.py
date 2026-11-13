"""Reference baseline R-1: long while the last CLOSED daily candle closes above its SMA(200). Execution on 1h.

Spot, long only, whole balance, no stop-loss (the SMA is the exit). It exists only to be beaten: a strategy that
does not beat buy-and-hold and this rule on a risk-adjusted out-of-sample basis is discarded. No free parameter
except the 200-day length, which is the textbook value.

Informative data: daily candles merged with freqtrade's merge_informative_pair (the daily values become visible
only after the day has closed, at 00:00 UTC of the next day). Freqtrade loads startup_candle_count candles of
EVERY timeframe used, so 200 daily candles are loaded for the SMA; 210 gives a margin.
"""

import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IStrategy, merge_informative_pair

SMA_DAYS = 200


class Sma200Baseline(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "1h"
    can_short = False

    minimal_roi = {"0": 100.0}
    stoploss = -0.99
    startup_candle_count = 210

    def informative_pairs(self):
        return [(pair, "1d") for pair in self.dp.current_whitelist()]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        daily = self.dp.get_pair_dataframe(metadata["pair"], "1d")
        daily["sma"] = ta.SMA(daily, timeperiod=SMA_DAYS)
        return merge_informative_pair(dataframe, daily, self.timeframe, "1d", ffill=True)

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            dataframe["sma_1d"].notna() & (dataframe["close_1d"] > dataframe["sma_1d"]) & (dataframe["volume"] > 0),
            ["enter_long", "enter_tag"],
        ] = (1, "daily_close_above_sma200")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            dataframe["sma_1d"].notna() & (dataframe["close_1d"] <= dataframe["sma_1d"]) & (dataframe["volume"] > 0),
            ["exit_long", "exit_tag"],
        ] = (1, "daily_close_below_sma200")
        return dataframe
