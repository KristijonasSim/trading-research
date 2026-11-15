"""research_scalp Track C — SCALP_C_listing: post-listing event-window momentum breakout.

FROZEN PARAMETERS (pre-declared in this header per Task 8 Step 3, before any backtest; do not tune):
  event window : [listing + 5d, listing + 60d) — listing dates from
                 research_scalp/data/listings.csv (keyed by base symbol)
  timeframe    : 5m, long only
  entry        : close > max(high of prior 96 candles)   (8h Donchian breakout)
                 AND 24h momentum close/close[-288] - 1 >= +3%
                 AND volume > 0
  stop         : chandelier — highest high since entry - 3 x ATR(96),
                 hard cap stoploss = -0.15 (never wider)
  exit         : custom_exit "event_end" at/after listing + 60d; no exit signal,
                 no ROI (minimal_roi disabled)
  position     : single position (MOT=1 via runner), leverage 1x, no position adjustment

G6 deviation (pre_reg §5, 2026-11-08): tradable pairs exclude the 60 Vision-resurrected
symbols in research_scalp/data/pairs_retry60.txt (freqtrade order sim needs live market
metadata). Track C tradable list = research_scalp/data/pairsC.txt (clean alive listings
only). Delisted coins' data is used for feasibility accounting only, never for positions.
"""
from datetime import datetime

import pandas as pd
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy


class SCALP_C_listing(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "5m"
    can_short = False
    stoploss = -0.15
    use_custom_stoploss = True
    minimal_roi = {"0": 100}
    startup_candle_count = 400
    process_only_new_candles = True

    # Frozen signal/risk parameters (see header — do not tune).
    BRK = 96        # 8h breakout lookback (prior highs)
    MOM = 288       # 24h momentum lookback (5m candles)
    MOM_MIN = 0.03  # +3% 24h momentum floor
    ATR_P = 96      # ATR period (8h)
    ATR_MULT = 3.0  # chandelier multiple
    DAY_START = 5   # event window start: listing + N days
    DAY_END = 60    # event window end:   listing + N days
    LISTINGS_CSV = "research_scalp/data/listings.csv"
    _listings_cache: dict | None = None

    @classmethod
    def _listings(cls) -> dict:
        if cls._listings_cache is None:
            df = pd.read_csv(cls.LISTINGS_CSV)
            cls._listings_cache = dict(zip(df["sym"], pd.to_datetime(df["listing"], utc=True)))
        return cls._listings_cache

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, entry_tag: str | None, side: str,
                 **kwargs) -> float:
        return 1.0

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=self.ATR_P)
        dataframe["brk_hi"] = dataframe["high"].rolling(self.BRK).max().shift(1)
        dataframe["mom24h"] = dataframe["close"] / dataframe["close"].shift(self.MOM) - 1.0
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["enter_long"] = 0
        listing = self._listings().get(metadata["pair"].split("/")[0])
        if listing is None:
            return dataframe
        t0 = listing + pd.Timedelta(days=self.DAY_START)
        t1 = listing + pd.Timedelta(days=self.DAY_END)
        in_win = (dataframe["date"] >= t0) & (dataframe["date"] < t1)
        cond = (in_win
                & dataframe["brk_hi"].notna() & dataframe["atr"].notna()
                & (dataframe["close"] > dataframe["brk_hi"])
                & (dataframe["mom24h"] >= self.MOM_MIN)
                & (dataframe["volume"] > 0))
        dataframe.loc[cond.values, "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0
        return dataframe

    def custom_exit(self, pair: str, trade: Trade, current_time: datetime,
                    current_rate: float, current_profit: float, **kwargs):
        listing = self._listings().get(pair.split("/")[0])
        if listing is None:
            return None
        if current_time >= listing + pd.Timedelta(days=self.DAY_END):
            return "event_end"
        return None

    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float, after_fill: bool,
                        **kwargs) -> float | None:
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if df is None or df.empty:
            return None
        df = df[df["date"] < current_time]  # completed candles only (no lookahead)
        if df.empty:
            return None
        atr = df.iloc[-1]["atr"]
        if pd.isna(atr) or atr <= 0:
            return None
        since = df[df["date"] >= trade.open_date_utc]
        hh = float(since["high"].max()) if not since.empty else float(df.iloc[-1]["high"])
        stop_abs = hh - self.ATR_MULT * float(atr)
        dist = (current_rate - stop_abs) / current_rate
        if dist <= 0:
            return -0.0001  # chandelier already breached: exit at once
        return max(-dist, self.stoploss)


class Stress_SCALP_C_listing_delay1(SCALP_C_listing):
    """Latency-1 stress: entry shifted one candle (Stress_OPT9_delay1 pattern)."""
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = super().populate_entry_trend(dataframe, metadata)
        df["enter_long"] = df["enter_long"].shift(1).fillna(0.0)
        return df
