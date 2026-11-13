"""H-015: time-series momentum on CLOSED daily candles, executed on 1h.

Rule: long while the N-day return of the last closed daily candle is positive, i.e. close(d) / close(d - N days) > 1.
Exit when it is no longer positive. Spot, long only, one position, whole allowed balance, no stop-loss (the signal
is the exit), no sizing hooks.

N_DAYS and USE_REGIME are module constants. The registered grid (N in 30, 60, 90, 120, 180; with and without the
regime filter = 10 configurations) is generated as temporary copies by research/tools/grid_explore.py; this file
keeps one reference configuration and is never edited to select a result.

Regime (USE_REGIME = True): regime_on() from regime_filter.py = daily close above its SMA(200) (vol_regime stays
off, see research/regime-filter-ablation.md). Entry needs the regime; the position also closes when it turns off.

Daily values reach the 1h frame through merge_informative_pair, so a day is used only after it has closed; orders
execute at the next 1h open. Freqtrade loads startup_candle_count candles of EVERY timeframe: 400 daily candles
cover N <= 180 and the SMA(200).
"""

import pandas as pd
from pandas import DataFrame

from freqtrade.strategy import IStrategy, merge_informative_pair
from regime_filter import regime_on

N_DAYS = 90
USE_REGIME = False


def momentum_positive(close_1d: pd.Series, n_days: int) -> pd.Series:
    """True when close(d) > close(d - n_days). Causal (looks back only); False while undefined."""
    return (close_1d / close_1d.shift(n_days) - 1.0 > 0.0).fillna(False)


class TimeSeriesMomentum_H015_v1(IStrategy):
    """N-day time-series momentum on closed daily candles."""

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
        daily["mom"] = momentum_positive(daily["close"], N_DAYS).astype(int)
        daily["regime"] = regime_on(daily["close"]).astype(int)
        return merge_informative_pair(dataframe, daily[["date", "mom", "regime"]], self.timeframe, "1d", ffill=True)

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        ok = dataframe["mom_1d"] == 1
        if USE_REGIME:
            ok = ok & (dataframe["regime_1d"] == 1)
        dataframe.loc[ok & (dataframe["volume"] > 0), ["enter_long", "enter_tag"]] = (1, "tsmom_positive")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        off = dataframe["mom_1d"] == 0
        if USE_REGIME:
            off = off | (dataframe["regime_1d"] == 0)
        dataframe.loc[off & (dataframe["volume"] > 0), ["exit_long", "exit_tag"]] = (1, "tsmom_not_positive")
        return dataframe
