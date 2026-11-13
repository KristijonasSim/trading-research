"""H-019: daily RSI(2) oversold dip buy inside a 200-day uptrend, exit above the 5-day SMA.

Signals use CLOSED daily candles. Daily values reach the 1h frame through merge_informative_pair, so a day is
used only after it has closed; orders execute at the next 1h open. Spot long only, one position, no pyramiding.

Indicators on daily closes: RSI(2) with Wilder smoothing (alpha = 1/2, seeded with the simple average of the
first 2 changes), SMA(200), SMA(5).
Entry: daily close > SMA(200) AND RSI(2) < 10.
Exit: daily close > SMA(5) OR daily close < SMA(200).
No stop in the rule: stoploss = -0.99 only satisfies the engine contract. No cooldown.
Freqtrade loads startup_candle_count candles of EVERY timeframe: 400 daily candles cover the SMA(200) plus
Wilder RSI stabilisation.
"""

import numpy as np
import pandas as pd
from pandas import DataFrame

from freqtrade.strategy import IStrategy, merge_informative_pair

RSI_LENGTH = 2
RSI_ENTRY = 10.0
TREND_DAYS = 200
EXIT_DAYS = 5


def wilder_rsi(close: pd.Series, length: int) -> pd.Series:
    """Wilder RSI seeded with the simple average of the first `length` changes. Causal; NaN while undefined."""
    values = close.to_numpy(dtype=float)
    n = len(values)
    out = np.full(n, np.nan)
    if n <= length:
        return pd.Series(out, index=close.index)
    delta = np.diff(values)
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    avg_gain = gain[:length].mean()
    avg_loss = loss[:length].mean()
    for i in range(length, n):
        if i > length:
            avg_gain = (avg_gain * (length - 1) + gain[i - 1]) / length
            avg_loss = (avg_loss * (length - 1) + loss[i - 1]) / length
        if np.isnan(avg_gain) or np.isnan(avg_loss):
            continue
        if avg_loss == 0:
            out[i] = 100.0 if avg_gain > 0 else 50.0
        else:
            out[i] = 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    return pd.Series(out, index=close.index)


class DailyRSI2Dip_H019_v1(IStrategy):
    """RSI(2) dip buy on closed daily candles, 200-day trend filter, 5-day SMA exit."""

    INTERFACE_VERSION = 3
    timeframe = "1h"
    can_short = False

    minimal_roi = {"0": 100.0}
    stoploss = -0.99
    startup_candle_count = 400

    def informative_pairs(self):
        return [(pair, "1d") for pair in self.dp.current_whitelist()]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        daily = self.dp.get_pair_dataframe(metadata["pair"], "1d")
        daily["dclose"] = daily["close"]
        daily["rsi2"] = wilder_rsi(daily["close"], RSI_LENGTH)
        daily["sma200"] = daily["close"].rolling(TREND_DAYS).mean()
        daily["sma5"] = daily["close"].rolling(EXIT_DAYS).mean()
        return merge_informative_pair(
            dataframe,
            daily[["date", "dclose", "rsi2", "sma200", "sma5"]],
            self.timeframe,
            "1d",
            ffill=True,
        )

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                dataframe["dclose_1d"].notna()
                & dataframe["rsi2_1d"].notna()
                & dataframe["sma200_1d"].notna()
                & (dataframe["dclose_1d"] > dataframe["sma200_1d"])
                & (dataframe["rsi2_1d"] < RSI_ENTRY)
                & (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"],
        ] = (1, "rsi2_dip")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                dataframe["dclose_1d"].notna()
                & dataframe["sma200_1d"].notna()
                & dataframe["sma5_1d"].notna()
                & (
                    (dataframe["dclose_1d"] > dataframe["sma5_1d"])
                    | (dataframe["dclose_1d"] < dataframe["sma200_1d"])
                )
                & (dataframe["volume"] > 0)
            ),
            ["exit_long", "exit_tag"],
        ] = (1, "above_sma5_or_below_sma200")
        return dataframe
