"""H-012: EMA(20) snapback, ATR-normalised, inside an EMA(200) uptrend (1h).

Spot, long only, one position, no DCA/martingale. Closed candles only; a signal
at the close of candle t is executed at the open of candle t+1.

Definitions (completed candles):
- z(t) = (close(t) - EMA20(t)) / ATR14(t): distance from the mean in ATRs.
- Stretch: min z over the previous LOOKBACK candles (t-LOOKBACK .. t-1) <= -Z_ENTRY.
- Trend: close(t) > EMA200(t).
- Confirmation: close(t) > high(t-1) (the first candle to close above the prior
  candle's high after the stretch) and close(t) < EMA20(t) (room left to the mean).
- Optional filters (off in the base rule): RSI14(t-1..) minimum over the lookback
  <= RSI_MAX; volume(t) >= VOLUME_MULT * mean volume of the previous 20 candles.
- Stop: close(t) - ATR_STOP_MULT * ATR14(t), fixed at entry (no trailing).
- Exit: first close >= EMA20 (executed next open), or time stop after
  MAX_HOLD_BARS candles. EXIT_MODE "rr" instead targets entry + RR_TARGET * risk.
- Cooldown COOLDOWN_BARS candles after any exit.

Sizing is not set here (sizing hooks are forbidden by the lab).
"""

import numpy as np
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IStrategy, stoploss_from_absolute

EMA_PERIOD = 20
TREND_PERIOD = 200
ATR_PERIOD = 14
Z_ENTRY = 2.0
LOOKBACK = 6
ATR_STOP_MULT = 2.0
MAX_HOLD_BARS = 48
COOLDOWN_BARS = 6
USE_RSI = False
RSI_MAX = 35.0
USE_VOLUME = False
VOLUME_MULT = 1.0
EXIT_MODE = "ema20"
RR_TARGET = 1.5
TIMEFRAME_HOURS = 1


def snapback_signal(
    high, close, volume, ema, trend, atr, rsi, *,
    z_entry=Z_ENTRY, lookback=LOOKBACK, use_rsi=USE_RSI, rsi_max=RSI_MAX,
    use_volume=USE_VOLUME, volume_mult=VOLUME_MULT,
):
    """Boolean entry signal; value at t uses only candles <= t.

    Inputs are pandas Series. Returns a boolean Series.
    """
    z = (close - ema) / atr
    stretched = z.shift(1).rolling(lookback).min() <= -z_entry
    signal = (
        stretched
        & (close > trend)
        & (close > high.shift(1))
        & (close < ema)
    )
    if use_rsi:
        signal &= rsi.shift(1).rolling(lookback).min() <= rsi_max
    if use_volume:
        signal &= volume >= volume_mult * volume.shift(1).rolling(20).mean()
    return (signal & atr.notna() & trend.notna()).fillna(False).astype(bool)


class EMASnapbackATR_H012_v1(IStrategy):
    """Buy the first confirmed recovery after an ATR-normalised stretch below EMA20."""

    INTERFACE_VERSION = 3
    timeframe = "1h"
    can_short = False

    minimal_roi = {"0": 100.0}
    stoploss = -0.30
    use_custom_stoploss = True
    use_exit_signal = True
    startup_candle_count = 800

    @property
    def protections(self):
        return [{"method": "CooldownPeriod", "stop_duration_candles": COOLDOWN_BARS}]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema20"] = ta.EMA(dataframe, timeperiod=EMA_PERIOD)
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=TREND_PERIOD)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=ATR_PERIOD)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["snap_signal"] = snapback_signal(
            dataframe["high"], dataframe["close"], dataframe["volume"],
            dataframe["ema20"], dataframe["ema200"], dataframe["atr"], dataframe["rsi"],
        )
        dataframe["snap_stop"] = dataframe["close"] - ATR_STOP_MULT * dataframe["atr"]
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            dataframe["snap_signal"] & (dataframe["volume"] > 0),
            ["enter_long", "enter_tag"],
        ] = (1, "ema20_snapback")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        if EXIT_MODE == "ema20":
            dataframe.loc[
                (dataframe["close"] >= dataframe["ema20"]) & (dataframe["volume"] > 0),
                ["exit_long", "exit_tag"],
            ] = (1, "close_at_ema20")
        return dataframe

    def _signal_candle(self, pair: str, trade):
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        earlier = dataframe.loc[dataframe["date"] < trade.open_date_utc]
        if earlier.empty:
            return None
        return earlier.iloc[-1]

    def custom_stoploss(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        candle = self._signal_candle(pair, trade)
        if candle is None or not candle["snap_signal"]:
            return None
        return stoploss_from_absolute(float(candle["snap_stop"]), current_rate, is_short=False)

    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        candle = self._signal_candle(pair, trade)
        if candle is None or not candle["snap_signal"]:
            return None
        if EXIT_MODE == "rr":
            risk = float(candle["close"]) - float(candle["snap_stop"])
            if current_rate >= float(candle["close"]) + RR_TARGET * risk:
                return "target_rr"
        held_hours = (current_time - trade.open_date_utc).total_seconds() / 3600.0
        if held_hours >= MAX_HOLD_BARS * TIMEFRAME_HOURS:
            return "time_stop"
        return None
