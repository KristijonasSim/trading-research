"""H-013: Triple Bottom reversal, confirmed by a close above the neckline (4h).

Identical rule and constants to H-011 (expressed in candles); only the timeframe differs.

Spot, long only, one position, no averaging down, no pyramiding. Closed
candles only; a signal at the close of candle t is executed at the open of
candle t+1.

Pattern (all measured on completed candles):
- Pivot low at i: low[i] is the lowest low of [i-K, i+K] (ties on the left
  allowed, on the right not). It is KNOWN only at the close of candle i+K,
  never earlier; the signal logic below never reads a pivot before that.
- Three consecutive pivot lows L1, L2, L3 (indices i1<i2<i3) form the support
  zone when (max(L)-min(L)) / mean(L) <= TOLERANCE and consecutive bottoms are at
  least MIN_SEPARATION candles apart and the whole pattern is at most MAX_SPAN long.
- The recoveries are the highest highs between the bottoms: H1 in (i1, i2) and
  H2 in (i2, i3). Each must be at least MIN_REBOUND above the mean bottom.
- Neckline = max(H1, H2).
- Entry at the first candle t >= i3+K (and <= i3+K+MAX_WAIT, before a fourth
  pivot is confirmed) whose CLOSE is above the neckline, provided that no earlier close
  since i3 was above it, no low since i3 fell below the support zone by more
  than TOLERANCE, volume(t) >= VOLUME_MULT * mean volume of the previous 20
  candles, and the optional RSI-divergence and EMA(200) filters pass.
- Stop = lowest bottom - ATR_STOP_MULT * ATR(14) at the signal candle.
  Target = neckline + TP_MULT * (neckline - mean bottom).
  Trade only if (target - close) / (close - stop) >= MIN_RR (default 0.0 = off: with
  the stop below the support and the entry at the neckline this ratio is below
  1 by construction, so any floor above ~0.9 removes every trade).
- Time stop after MAX_HOLD_BARS candles without stop or target.
- A pattern signals once, and a later pattern must start after the previous
  signalled pattern's last bottom (no reuse of bottoms: no duplicate entries).

Sizing is not set here (position sizing hooks are forbidden by the lab). The
risk-based size is a pure function `risk_position_fraction`, applied by the
research analysis to the exported trades and available to the live layer.
"""

import numpy as np
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IStrategy, stoploss_from_absolute

PIVOT_K = 5
TOLERANCE = 0.02
MIN_SEPARATION = 12
MAX_SPAN = 150
MIN_REBOUND = 0.03
MAX_WAIT = 30
VOLUME_MULT = 1.0
ATR_STOP_MULT = 0.5
TP_MULT = 1.0
MIN_RR = 0.0
USE_RSI_DIVERGENCE = False
USE_EMA200 = False
VOLUME_WINDOW = 20
MAX_HOLD_BARS = 150
TIMEFRAME_HOURS = 4


def pivot_low_flags(low: np.ndarray, k: int) -> np.ndarray:
    """flags[j] is True when the candle j-k is a pivot low, evaluated at j.

    Uses only candles <= j. low[j-k] must be <= every low in [j-2k, j-k-1] and
    < every low in [j-k+1, j].
    """
    n = len(low)
    flags = np.zeros(n, dtype=bool)
    if n < 2 * k + 1:
        return flags
    windows = np.lib.stride_tricks.sliding_window_view(low, 2 * k + 1)  # windows[m] = low[m .. m+2k]
    centre = windows[:, k]
    left_min = windows[:, :k].min(axis=1)
    right_min = windows[:, k + 1 :].min(axis=1)
    is_pivot = (centre <= left_min) & (centre < right_min)
    flags[2 * k :] = is_pivot  # window m is centred on i = m+k and known at j = m+2k
    return flags


def find_triple_bottom_signals(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    volume: np.ndarray,
    atr: np.ndarray,
    rsi: np.ndarray,
    ema200: np.ndarray,
    *,
    k: int = PIVOT_K,
    tolerance: float = TOLERANCE,
    min_separation: int = MIN_SEPARATION,
    max_span: int = MAX_SPAN,
    min_rebound: float = MIN_REBOUND,
    max_wait: int = MAX_WAIT,
    volume_mult: float = VOLUME_MULT,
    atr_stop_mult: float = ATR_STOP_MULT,
    tp_mult: float = TP_MULT,
    min_rr: float = MIN_RR,
    use_rsi_divergence: bool = USE_RSI_DIVERGENCE,
    use_ema200: bool = USE_EMA200,
):
    """Signals of the pattern. Returns (signal, stop, target, neckline, i3) arrays.

    The value at index t depends only on candles <= t: the signal array of a
    prefix of the data equals the prefix of the signal array of the full data.
    """
    n = len(close)
    signal = np.zeros(n, dtype=bool)
    stop = np.full(n, np.nan)
    target = np.full(n, np.nan)
    neckline_out = np.full(n, np.nan)
    pivot_out = np.full(n, -1, dtype=np.int64)

    flags = pivot_low_flags(low, k)
    # Pivot candle indices in order of confirmation (pivot i confirmed at i+k).
    pivots = [j - k for j in np.flatnonzero(flags)]
    confirm_at = [p + k for p in pivots]
    vol_mean = np.full(n, np.nan)
    if n > VOLUME_WINDOW:
        csum = np.cumsum(np.insert(np.nan_to_num(volume), 0, 0.0))
        vol_mean[VOLUME_WINDOW:] = (csum[VOLUME_WINDOW:n] - csum[: n - VOLUME_WINDOW]) / VOLUME_WINDOW

    last_used_i3 = -1
    for index in range(2, len(pivots)):
        i1, i2, i3 = pivots[index - 2], pivots[index - 1], pivots[index]
        if i1 <= last_used_i3:
            continue
        known_from = confirm_at[index]
        # a fourth confirmed pivot replaces this triple, so the window ends before it
        next_confirm = confirm_at[index + 1] if index + 1 < len(pivots) else n
        window_end = min(known_from + max_wait, next_confirm - 1, n - 1)
        if window_end < known_from:
            continue
        if i2 - i1 < min_separation or i3 - i2 < min_separation or i3 - i1 > max_span:
            continue
        bottoms = np.array([low[i1], low[i2], low[i3]])
        mean_bottom = float(bottoms.mean())
        if mean_bottom <= 0 or (bottoms.max() - bottoms.min()) / mean_bottom > tolerance:
            continue
        peak1 = float(np.max(high[i1 : i2 + 1]))
        peak2 = float(np.max(high[i2 : i3 + 1]))
        if min(peak1, peak2) < mean_bottom * (1.0 + min_rebound):
            continue
        neckline = max(peak1, peak2)
        support_floor = float(bottoms.min()) * (1.0 - tolerance)
        if use_rsi_divergence and not (rsi[i3] > rsi[i1] and not np.isnan(rsi[i3]) and not np.isnan(rsi[i1])):
            continue

        for t in range(known_from, window_end + 1):
            if np.min(low[i3 : t + 1]) < support_floor:
                break
            if close[t] > neckline:
                if np.isnan(atr[t]) or np.isnan(vol_mean[t]) or vol_mean[t] <= 0:
                    break
                if volume[t] < volume_mult * vol_mean[t]:
                    break
                if use_ema200 and not (close[t] > ema200[t]):
                    break
                stop_price = float(bottoms.min()) - atr_stop_mult * float(atr[t])
                target_price = neckline + tp_mult * (neckline - mean_bottom)
                risk = close[t] - stop_price
                if risk <= 0 or (target_price - close[t]) / risk < min_rr:
                    break
                signal[t] = True
                stop[t] = stop_price
                target[t] = target_price
                neckline_out[t] = neckline
                pivot_out[t] = i3
                last_used_i3 = i3
                break
    return signal, stop, target, neckline_out, pivot_out


def risk_position_fraction(risk_fraction: float, entry: float, stop: float, cap: float = 1.0) -> float:
    """Share of the account to commit so that hitting the stop loses `risk_fraction`.

    fraction = risk_fraction / ((entry - stop) / entry), capped at `cap` (spot,
    no leverage). Returns 0.0 for an invalid stop.
    """
    if entry <= 0 or stop >= entry or risk_fraction <= 0:
        return 0.0
    return min(cap, risk_fraction / ((entry - stop) / entry))


class TripleBottomReversal_H013_v1(IStrategy):
    """Triple Bottom reversal confirmed by a neckline close."""

    INTERFACE_VERSION = 3
    timeframe = "4h"
    can_short = False

    minimal_roi = {"0": 100.0}
    stoploss = -0.30
    use_custom_stoploss = True
    use_exit_signal = False
    startup_candle_count = 800

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)
        signal, stop, target, neckline, pivot = find_triple_bottom_signals(
            dataframe["high"].to_numpy(dtype=float),
            dataframe["low"].to_numpy(dtype=float),
            dataframe["close"].to_numpy(dtype=float),
            dataframe["volume"].to_numpy(dtype=float),
            dataframe["atr"].to_numpy(dtype=float),
            dataframe["rsi"].to_numpy(dtype=float),
            dataframe["ema200"].to_numpy(dtype=float),
        )
        dataframe["tb_signal"] = signal
        dataframe["tb_stop"] = stop
        dataframe["tb_target"] = target
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            dataframe["tb_signal"] & (dataframe["volume"] > 0),
            ["enter_long", "enter_tag"],
        ] = (1, "triple_bottom_neckline")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe

    def _signal_candle(self, pair: str, trade):
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        earlier = dataframe.loc[dataframe["date"] < trade.open_date_utc]
        if earlier.empty:
            return None
        return earlier.iloc[-1]

    def custom_stoploss(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        candle = self._signal_candle(pair, trade)
        if candle is None or not candle["tb_signal"]:
            return None
        return stoploss_from_absolute(float(candle["tb_stop"]), current_rate, is_short=False)

    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        candle = self._signal_candle(pair, trade)
        if candle is None or not candle["tb_signal"]:
            return None
        if current_rate >= float(candle["tb_target"]):
            return "target_pattern_height"
        held_hours = (current_time - trade.open_date_utc).total_seconds() / 3600.0
        if held_hours >= MAX_HOLD_BARS * TIMEFRAME_HOURS:
            return "time_stop"
        return None
