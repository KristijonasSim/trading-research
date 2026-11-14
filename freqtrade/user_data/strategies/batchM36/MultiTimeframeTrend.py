"""
MultiTimeframeTrend - Saf Trend Takip Stratejisi (Benchmark)
=============================================================
Ortalamaya dönüş OLMADAN sadece EMA crossover + ADX ile trend takibi.
Ana stratejinin trend bileşeninin tek başına performansını ölçmek için
benchmark olarak kullanılır.

Mantık:
  1. 1d: EMA_50 > EMA_200 → BOĞA
  2. 1h: EMA_12 > EMA_26 VE ADX > 25 → LONG giriş
  3. EMA_12 < EMA_26 → çıkış
"""

import logging
from functools import reduce

import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IntParameter, IStrategy, merge_informative_pair

logger = logging.getLogger(__name__)


class MultiTimeframeTrend(IStrategy):
    """Saf EMA Crossover Trend Following - Mean reversion yok."""

    INTERFACE_VERSION = 3
    timeframe = "1h"
    can_short = False

    minimal_roi = {
        "0": 0.06,
        "60": 0.04,
        "120": 0.03,
        "240": 0.015,
    }

    stoploss = -0.06
    trailing_stop = True
    trailing_stop_positive = 0.03
    trailing_stop_positive_offset = 0.04
    trailing_only_offset_is_reached = True

    # Protections
    protections = [
        {"method": "CooldownPeriod", "stop_duration_candles": 5},
        {"method": "StoplossGuard", "trade_limit": 3, "stop_duration_candles": 12, "only_per_pair": True},
    ]

    startup_candle_count = 200

    # Hyperopt parametreleri
    adx_threshold = IntParameter(15, 35, default=25, space="buy", optimize=True)

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        return [(pair, "1d") for pair in pairs]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 1h indikatörler
        dataframe["ema_12"] = ta.EMA(dataframe["close"], timeperiod=12)
        dataframe["ema_26"] = ta.EMA(dataframe["close"], timeperiod=26)
        dataframe["adx"] = ta.ADX(dataframe["high"], dataframe["low"], dataframe["close"], timeperiod=14)
        dataframe["plus_di"] = ta.PLUS_DI(dataframe["high"], dataframe["low"], dataframe["close"], timeperiod=14)
        dataframe["minus_di"] = ta.MINUS_DI(dataframe["high"], dataframe["low"], dataframe["close"], timeperiod=14)
        dataframe["atr"] = ta.ATR(dataframe["high"], dataframe["low"], dataframe["close"], timeperiod=14)

        # 1d trend
        informative = self.dp.get_pair_dataframe(pair=metadata["pair"], timeframe="1d")
        if not informative.empty:
            informative["ema_50"] = ta.EMA(informative["close"], timeperiod=50)
            informative["ema_200"] = ta.EMA(informative["close"], timeperiod=200)
            informative["daily_trend"] = (informative["ema_50"] > informative["ema_200"]).astype(int)
            dataframe = merge_informative_pair(dataframe, informative, self.timeframe, "1d", ffill=True)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = [
            dataframe["ema_12"] > dataframe["ema_26"],
            dataframe["adx"] > self.adx_threshold.value,
            dataframe["plus_di"] > dataframe["minus_di"],
            dataframe["volume"] > 0,
        ]
        if "daily_trend_1d" in dataframe.columns:
            conditions.append(dataframe["daily_trend_1d"] == 1)
        else:
            logger.warning(f"Daily trend data missing for {metadata['pair']} - no signals generated")
            return dataframe

        dataframe.loc[reduce(lambda x, y: x & y, conditions), "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["ema_12"] < dataframe["ema_26"]) | (dataframe["adx"] < 20),
            "exit_long",
        ] = 1
        return dataframe
