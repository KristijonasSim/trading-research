"""H-018: Donchian ensemble, majority vote of four daily channels, no stop. Execution on 1h.

Members (N, M): (20,10), (55,20), (100,50), (200,100). Each member is a two-level latch on the daily frame:
ON when daily close > rolling(N).max() of daily highs shifted by one day; OFF when daily close < rolling(M).min() of
daily lows shifted by one day; otherwise the previous state is kept; undefined channel values give OFF.
Entry while at least 2 members are ON, exit when fewer than 2 are ON. Daily values are merged with
merge_informative_pair (visible only after the day closed). No stop (stoploss only satisfies the engine contract).
"""

import numpy as np
from pandas import DataFrame

from freqtrade.strategy import IStrategy, merge_informative_pair

MEMBERS = ((20, 10), (55, 20), (100, 50), (200, 100))
VOTE_THRESHOLD = 2


def _latch(close, upper, lower):
    state = np.zeros(len(close), dtype=float)
    previous = 0.0
    for i in range(len(close)):
        u, l, c = upper[i], lower[i], close[i]
        if np.isnan(u) or np.isnan(l) or np.isnan(c):
            previous = 0.0
        elif c > u:
            previous = 1.0
        elif c < l:
            previous = 0.0
        state[i] = previous
    return state


class DonchianEnsemble_H018_v1(IStrategy):
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
        votes = np.zeros(len(daily), dtype=float)
        close = daily["close"].to_numpy(dtype=float)
        for n, m in MEMBERS:
            upper = daily["high"].rolling(n).max().shift(1).to_numpy(dtype=float)
            lower = daily["low"].rolling(m).min().shift(1).to_numpy(dtype=float)
            votes = votes + _latch(close, upper, lower)
        daily["votes"] = votes
        keep = daily[["date", "votes"]]
        return merge_informative_pair(dataframe, keep, self.timeframe, "1d", ffill=True)

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            dataframe["votes_1d"].notna()
            & (dataframe["votes_1d"] >= VOTE_THRESHOLD)
            & (dataframe["volume"] > 0),
            ["enter_long", "enter_tag"],
        ] = (1, "donchian_vote_on")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            dataframe["votes_1d"].notna()
            & (dataframe["votes_1d"] < VOTE_THRESHOLD)
            & (dataframe["volume"] > 0),
            ["exit_long", "exit_tag"],
        ] = (1, "donchian_vote_off")
        return dataframe
