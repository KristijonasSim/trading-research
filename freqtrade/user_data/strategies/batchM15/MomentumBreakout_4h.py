# MomentumBreakout_4h.py - v2
#
# PURPOSE: Catches sustained rallies like the Aug 19 BTC +6% move.
# Enters EARLY in a momentum move, not after full bull confirmation.
#
# KEY DESIGN DECISIONS:
#   - 90-candle (3-week) consolidation window — only genuine multi-week breakouts
#   - 2x volume requirement — real institutional buying, not noise
#   - ADX > 25 and rising with +DI > -DI — confirmed trend direction
#   - Daily regime: blocks on death cross + RSI<45 only — allows early-stage rallies
#   - Trailing stop: lets winners run, 3% trail activates at +5%
#
# COMPLEMENTS:
#   BinHV45: buys drops. MomentumBreakout: buys breakouts. Together they cover
#   both directions of meaningful price moves.

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from freqtrade.strategy import IStrategy, informative
from pandas import DataFrame
import pandas_ta as pta
import pandas as pd


class MomentumBreakout_4h(IStrategy):

    minimal_roi = {
        "0":    0.15,   # let trailing stop do the work
        "2880": 0.08,   # 8% after 30 days
        "5760": 0.04,   # 4% after 60 days
    }

    stoploss = -0.05
    trailing_stop = True
    trailing_stop_positive = 0.03
    trailing_stop_positive_offset = 0.05
    trailing_only_offset_is_reached = True

    timeframe = "4h"
    startup_candle_count: int = 250

    # ------------------------------------------------------------------ #
    # 1d INFORMER — daily bear detection                                   #
    # ------------------------------------------------------------------ #
    @informative('1d')
    def populate_indicators_1d(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema_50"]  = pta.ema(dataframe["close"], length=50)
        dataframe["ema_200"] = pta.ema(dataframe["close"], length=200)
        dataframe["rsi"]     = pta.rsi(dataframe["close"], length=14)
        dataframe["daily_bear"] = (
            (dataframe["close"] < dataframe["ema_200"].fillna(0)) &
            (dataframe["ema_50"].fillna(0) < dataframe["ema_200"].fillna(float("inf"))) &
            (dataframe["rsi"].fillna(50) < 45)
        ).astype(int)
        return dataframe

    # ------------------------------------------------------------------ #
    # 4h INDICATORS                                                        #
    # ------------------------------------------------------------------ #
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema_20"] = pta.ema(dataframe["close"], length=20)
        dataframe["ema_50"] = pta.ema(dataframe["close"], length=50)
        dataframe["rsi"]    = pta.rsi(dataframe["close"], length=14)

        adx = pta.adx(dataframe["high"], dataframe["low"], dataframe["close"], length=14)
        if adx is not None and "ADX_14" in adx.columns:
            dataframe["adx"]     = adx["ADX_14"]
            dataframe["adx_pos"] = adx["DMP_14"]
            dataframe["adx_neg"] = adx["DMN_14"]
        else:
            dataframe["adx"]     = 0
            dataframe["adx_pos"] = 0
            dataframe["adx_neg"] = 0

        dataframe["vol_ma_20"] = pta.sma(dataframe["volume"], length=20)

        # 3-week consolidation window (90 x 4h candles)
        dataframe["consolidation_high"]  = dataframe["high"].shift(1).rolling(90).max()
        dataframe["consolidation_low"]   = dataframe["low"].shift(1).rolling(90).min()
        dataframe["consolidation_range"] = (
            (dataframe["consolidation_high"] - dataframe["consolidation_low"])
            / dataframe["consolidation_low"].replace(0, float("inf"))
        )

        dataframe["adx_rising"] = (dataframe["adx"] > dataframe["adx"].shift(2)).astype(int)
        return dataframe

    # ------------------------------------------------------------------ #
    # ENTRY                                                                #
    # ------------------------------------------------------------------ #
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        not_daily_bear = (
            dataframe["1d_daily_bear"] == 0
            if "1d_daily_bear" in dataframe.columns
            else pd.Series(True, index=dataframe.index)
        )

        dataframe.loc[
            (
                not_daily_bear &

                # Genuine 3-week consolidation breakout
                (dataframe["close"] > dataframe["consolidation_high"]) &
                (dataframe["consolidation_range"] > 0.08) &
                (dataframe["consolidation_range"] < 0.40) &

                # Strong bullish candle
                (dataframe["close"] > dataframe["open"]) &

                # 2x volume surge
                (dataframe["volume"] > dataframe["vol_ma_20"] * 2.0) &

                # RSI in momentum zone
                (dataframe["rsi"] > 52) &
                (dataframe["rsi"] < 75) &

                # Strong trend forming
                (dataframe["adx"] > 25) &
                (dataframe["adx_rising"] == 1) &
                (dataframe["adx_pos"] > dataframe["adx_neg"]) &

                # Price above short-term structure
                (dataframe["close"] > dataframe["ema_20"]) &
                (dataframe["close"] > dataframe["ema_50"]) &

                (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, "exit_long"] = 0
        return dataframe
