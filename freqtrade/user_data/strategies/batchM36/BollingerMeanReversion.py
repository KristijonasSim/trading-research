"""
BollingerMeanReversion - Saf Ortalamaya Dönüş Stratejisi (Benchmark)
=====================================================================
Trend filtresi OLMADAN sadece Bollinger Bands + RSI ile giriş/çıkış.
Ana stratejinin (TrendReversionStrategy) trend filtresinin fark yaratıp
yaratmadığını ölçmek için benchmark olarak kullanılır.

Mantık:
  1. close < BB_lower VE RSI < 30 → LONG giriş
  2. close > BB_middle → çıkış
"""

import logging
from functools import reduce

import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import DecimalParameter, IntParameter, IStrategy

logger = logging.getLogger(__name__)


class BollingerMeanReversion(IStrategy):
    """Saf Bollinger Bands Mean Reversion - Trend filtresi yok."""

    INTERFACE_VERSION = 3
    timeframe = "1h"
    can_short = False

    minimal_roi = {
        "0": 0.08,
        "30": 0.04,
        "60": 0.02,
        "120": 0.01,
    }

    stoploss = -0.04
    trailing_stop = True
    trailing_stop_positive = 0.015
    trailing_stop_positive_offset = 0.025
    trailing_only_offset_is_reached = True

    # Protections
    protections = [
        {"method": "CooldownPeriod", "stop_duration_candles": 5},
        {"method": "StoplossGuard", "trade_limit": 3, "stop_duration_candles": 12, "only_per_pair": True},
    ]

    startup_candle_count = 50

    # Hyperopt parametreleri
    buy_rsi = IntParameter(20, 40, default=30, space="buy", optimize=True)
    buy_bb_std = DecimalParameter(1.5, 2.5, default=2.0, decimals=1, space="buy", optimize=True)
    sell_rsi = IntParameter(60, 80, default=70, space="sell", optimize=True)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        bb_upper, bb_middle, bb_lower = ta.BBANDS(dataframe["close"], timeperiod=20, nbdevup=self.buy_bb_std.value, nbdevdn=self.buy_bb_std.value)
        dataframe["bb_upper"] = bb_upper
        dataframe["bb_middle"] = bb_middle
        dataframe["bb_lower"] = bb_lower

        dataframe["rsi"] = ta.RSI(dataframe["close"], timeperiod=14)
        dataframe["volume_sma"] = ta.SMA(dataframe["volume"], timeperiod=20)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = [
            dataframe["close"] < dataframe["bb_lower"],
            dataframe["rsi"] < self.buy_rsi.value,
            dataframe["volume"] > 0,
        ]
        dataframe.loc[reduce(lambda x, y: x & y, conditions), "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["close"] > dataframe["bb_middle"])
            | (dataframe["rsi"] > self.sell_rsi.value),
            "exit_long",
        ] = 1
        return dataframe
