import numpy as np
import pandas as pd
from pandas import DataFrame
from typing import Optional, Union

from freqtrade.strategy import IStrategy
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib


class AggressiveFreqaiStrategy(IStrategy):
    """
    Custom Aggressive FreqAI Strategy using LightGBM.
    Combines quantitative indicators (RSI, MACD, Bollinger Bands, ATR, Volume)
    with LightGBM targets for aggressive yet safe trading.
    """
    INTERFACE_VERSION = 3

    # Minimal ROI designed for 1:4 Risk:Reward ratio (Stoploss 1.5% -> Target 6.0%)
    minimal_roi = {
        "0": 0.06,     # +6.0% (1:4 Risk:Reward ratio based on -1.5% stoploss)
        "15": 0.045,   # +4.5% target after 15 minutes
        "30": 0.03,    # +3.0% target after 30 minutes
        "60": 0.015    # +1.5% target after 60 minutes
    }

    # Strict Stoploss (-1.5%) for 1:4 Risk:Reward setup
    stoploss = -0.015

    # Trailing stop loss to lock in profits
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.015
    trailing_only_offset_is_reached = True

    # Timeframe
    timeframe = "5m"

    # Process only new candles
    process_only_new_candles = True

    # Use exit signal
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # Startup candle count - ensures Freqtrade automatically fetches full historical data for new pairs
    startup_candle_count: int = 1000

    def feature_engineering_expand_all(
        self, dataframe: DataFrame, period: int, metadata: dict, **kwargs
    ) -> DataFrame:
        """
        Define multi-period feature engineering for FreqAI.
        """
        # RSI
        dataframe[f"%-rsi-period_{period}"] = ta.RSI(dataframe, timeperiod=period)

        # MACD
        macd = ta.MACD(dataframe)
        dataframe[f"%-macd-period_{period}"] = macd["macd"]
        dataframe[f"%-macdsignal-period_{period}"] = macd["macdsignal"]
        dataframe[f"%-macdhist-period_{period}"] = macd["macdhist"]

        # Bollinger Bands
        bollinger = ta.BBANDS(dataframe, timeperiod=period)
        dataframe[f"%-bb_lower-period_{period}"] = bollinger["lowerband"]
        dataframe[f"%-bb_middle-period_{period}"] = bollinger["middleband"]
        dataframe[f"%-bb_upper-period_{period}"] = bollinger["upperband"]
        dataframe[f"%-bb_width-period_{period}"] = (
            (bollinger["upperband"] - bollinger["lowerband"]) / bollinger["middleband"]
        )

        # ATR (Volatility)
        dataframe[f"%-atr-period_{period}"] = ta.ATR(dataframe, timeperiod=period)

        # Volume Momentum
        dataframe[f"%-volume_mean-period_{period}"] = dataframe["volume"].rolling(period).mean()

        return dataframe

    def feature_engineering_expand_basic(
        self, dataframe: DataFrame, metadata: dict, **kwargs
    ) -> DataFrame:
        """
        Basic single-timeframe features.
        """
        dataframe["%-pct_change"] = dataframe["close"].pct_change()
        dataframe["%-raw_volume"] = dataframe["volume"]
        dataframe["%-raw_price"] = dataframe["close"]

        return dataframe

    def feature_engineering_standard(
        self, dataframe: DataFrame, metadata: dict, **kwargs
    ) -> DataFrame:
        """
        Standard feature engineering called for each timeframe.
        """
        dataframe["%-day_of_week"] = dataframe["date"].dt.dayofweek
        dataframe["%-hour"] = dataframe["date"].dt.hour

        return dataframe

    def set_freqai_targets(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        """
        Set future price targets to train LightGBM model.
        Target: Percentage price change over label_period_candles into the future.
        """
        label_period = self.config["freqai"]["feature_parameters"]["label_period_candles"]

        # Target = (future_close - current_close) / current_close
        dataframe["&-target"] = (
            dataframe["close"].shift(-label_period) - dataframe["close"]
        ) / dataframe["close"]

        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate FreqAI indicators and predictions.
        """
        dataframe = self.freqai.start(dataframe, metadata, self)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Entry signals based on FreqAI model prediction and confidence score.
        """
        enter_long_conditions = [
            dataframe["do_predict"] == 1,
            dataframe["&-target"] > 0.003,  # Relaksasi: Target predicted return > 0.3% (dari 0.8%)
            dataframe["volume"] > 0,         # Volume check
        ]

        if "DI_values" in dataframe.columns:
            enter_long_conditions.append(dataframe["DI_values"] < 1.5)

        if enter_long_conditions:
            dataframe.loc[
                np.logical_and.reduce(enter_long_conditions), ["enter_long", "enter_tag"]
            ] = (1, "freqai_long_entry")

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Exit signals based on FreqAI target prediction.
        """
        exit_long_conditions = [
            dataframe["do_predict"] == 1,
            dataframe["&-target"] < -0.005,  # Target predicted drop < -0.5%
        ]

        if exit_long_conditions:
            dataframe.loc[
                np.logical_and.reduce(exit_long_conditions), ["exit_long", "exit_tag"]
            ] = (1, "freqai_long_exit")

        return dataframe
