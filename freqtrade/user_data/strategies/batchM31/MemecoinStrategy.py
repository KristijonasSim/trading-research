"""
MemecoinStrategy for Freqtrade
==============================
Designed for high-volatility memecoin trading simulation.

Entry logic:
  Volume spike (current volume > N * rolling average) combined with
  RSI momentum and EMA trend confirmation.

Exit logic:
  RSI overbought, EMA crossunder, or MACD histogram flip.
  Trailing stop to lock in profits on pumps.

Costs modelled:
  Taker fee 0.1% per side = 0.2% round-trip (set in config).
  Slippage is approximated by using order-book top-1 pricing.
"""

from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from pandas import DataFrame
import talib.abstract as ta
import numpy as np


class MemecoinStrategy(IStrategy):

    INTERFACE_VERSION = 3

    # --- ROI: take profits quickly, memecoins can reverse hard ---------------
    minimal_roi = {
        "0":   0.06,   # 6 % immediately
        "30":  0.04,   # 4 % after 30 min
        "60":  0.025,  # 2.5 % after 1 h
        "120": 0.015,  # 1.5 % after 2 h
        "240": 0.01,   # 1 % after 4 h
    }

    # --- Stop-loss: tight because memecoins dump without warning --------------
    stoploss = -0.08   # 8 %

    # Trailing stop activates once +4 % is reached, then trails at 2 %
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.04
    trailing_only_offset_is_reached = True

    timeframe = "5m"

    # Need enough history for EMA-50 and 24-candle volume mean
    startup_candle_count = 60

    # Freqtrade will use order-book top-1 for realistic fill prices
    use_entry_signal = True
    entry_profit_only = False
    ignore_roi_if_entry_signal = False

    # --- Hyperopt parameter ranges -------------------------------------------
    buy_volume_factor  = DecimalParameter(1.5,  4.0,  default=2.0,  space="buy",  optimize=True)
    buy_rsi_min        = IntParameter    (25,   50,   default=35,   space="buy",  optimize=True)
    buy_rsi_max        = IntParameter    (50,   70,   default=60,   space="buy",  optimize=True)
    buy_ema_gap        = DecimalParameter(0.0,  0.5,  default=0.1,  space="buy",  optimize=True)

    sell_rsi_threshold = IntParameter    (65,   85,   default=75,   space="sell", optimize=True)

    # -------------------------------------------------------------------------

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        # Trend EMAs
        dataframe["ema9"]  = ta.EMA(dataframe, timeperiod=9)
        dataframe["ema21"] = ta.EMA(dataframe, timeperiod=21)
        dataframe["ema50"] = ta.EMA(dataframe, timeperiod=50)

        # RSI
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        # MACD
        macd = ta.MACD(dataframe, fastperiod=12, slowperiod=26, signalperiod=9)
        dataframe["macd"]       = macd["macd"]
        dataframe["macdsignal"] = macd["macdsignal"]
        dataframe["macdhist"]   = macd["macdhist"]

        # Bollinger Bands (used in plots / optional conditions)
        boll = ta.BBANDS(dataframe, timeperiod=20, nbdevup=2.0, nbdevdn=2.0)
        dataframe["bb_upper"] = boll["upperband"]
        dataframe["bb_lower"] = boll["lowerband"]
        dataframe["bb_mid"]   = boll["middleband"]

        # ATR – volatility reference, also used for dynamic SL in future work
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)

        # Volume spike detection
        dataframe["volume_mean_24"] = (
            dataframe["volume"].rolling(window=24, min_periods=1).mean()
        )
        dataframe["volume_ratio"] = (
            dataframe["volume"] / dataframe["volume_mean_24"]
        ).replace([np.inf, -np.inf], 0)

        # Stochastic RSI – secondary confirmation
        stoch = ta.STOCHRSI(dataframe, timeperiod=14, fastk_period=5, fastd_period=3)
        dataframe["fastk"] = stoch["fastk"]
        dataframe["fastd"] = stoch["fastd"]

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        dataframe.loc[
            (
                # Volume spike signals growing interest or pump start
                (dataframe["volume_ratio"] > self.buy_volume_factor.value)

                # RSI in momentum zone: rising but not yet overbought
                & (dataframe["rsi"] > self.buy_rsi_min.value)
                & (dataframe["rsi"] < self.buy_rsi_max.value)

                # Short-term uptrend: price above EMA-9 and EMA-9 above EMA-21
                & (dataframe["close"] > dataframe["ema9"])
                & (dataframe["ema9"]  > dataframe["ema21"])

                # Medium-term trend positive: EMA-21 above EMA-50 (or close)
                & (dataframe["ema21"] > dataframe["ema50"] * (1 - self.buy_ema_gap.value / 100))

                # MACD histogram positive and growing
                & (dataframe["macdhist"] > 0)
                & (dataframe["macdhist"] > dataframe["macdhist"].shift(1))

                # Not at extreme Bollinger Band (avoid buying tops)
                & (dataframe["close"] < dataframe["bb_upper"] * 0.98)

                # Stoch RSI not overbought
                & (dataframe["fastk"] < 85)

                # Candle must have real volume
                & (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        dataframe.loc[
            (
                # RSI overbought
                (dataframe["rsi"] > self.sell_rsi_threshold.value)

                # OR: price crossed below fast EMA (momentum gone)
                | (
                    (dataframe["close"] < dataframe["ema9"])
                    & (dataframe["close"].shift(1) >= dataframe["ema9"].shift(1))
                )

                # OR: MACD histogram flipped negative
                | (
                    (dataframe["macdhist"] < 0)
                    & (dataframe["macdhist"].shift(1) >= 0)
                )
            ),
            "exit_long",
        ] = 1

        return dataframe
