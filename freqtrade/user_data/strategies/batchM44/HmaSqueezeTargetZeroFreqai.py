from __future__ import annotations

import numpy as np
from pandas import DataFrame

from freqtrade.strategy import IStrategy

from hma_squeeze_ratio import (
    add_freqai_feature_columns,
    add_hma_squeeze_ratio_indicators,
)
from target_engineering import TARGET_ZERO_COLUMN, calculate_target_zero


class HmaSqueezeTargetZeroFreqai(IStrategy):
    timeframe = "15m"
    can_short = True
    process_only_new_candles = True
    startup_candle_count = 2400

    minimal_roi = {"0": 0.03}
    stoploss = -0.05
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    prediction_zscore = 0.0

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = add_hma_squeeze_ratio_indicators(dataframe)
        dataframe = self.freqai.start(dataframe, metadata, self)
        dataframe["target_roi"] = (
            dataframe[f"{TARGET_ZERO_COLUMN}_mean"]
            + dataframe[f"{TARGET_ZERO_COLUMN}_std"] * self.prediction_zscore
        )
        dataframe["sell_roi"] = (
            dataframe[f"{TARGET_ZERO_COLUMN}_mean"]
            - dataframe[f"{TARGET_ZERO_COLUMN}_std"] * self.prediction_zscore
        )
        return dataframe

    def feature_engineering_expand_all(
        self,
        dataframe: DataFrame,
        period: int,
        metadata: dict,
        **kwargs,
    ) -> DataFrame:
        log_return = np.log(dataframe["close"]).diff()
        ema = dataframe["close"].ewm(span=period, adjust=False).mean()
        volume_mean = dataframe["volume"].rolling(period).mean()

        dataframe["%-ema_distance-period"] = (dataframe["close"] - ema) / dataframe["close"]
        dataframe["%-return_std-period"] = log_return.rolling(period).std()
        dataframe["%-volume_distance-period"] = dataframe["volume"] / volume_mean - 1
        return dataframe

    def feature_engineering_expand_basic(
        self,
        dataframe: DataFrame,
        metadata: dict,
        **kwargs,
    ) -> DataFrame:
        dataframe = add_hma_squeeze_ratio_indicators(dataframe)
        dataframe = add_freqai_feature_columns(dataframe)
        return dataframe

    def feature_engineering_standard(
        self,
        dataframe: DataFrame,
        metadata: dict,
        **kwargs,
    ) -> DataFrame:
        dataframe["%-day_of_week"] = dataframe["date"].dt.dayofweek
        dataframe["%-hour"] = dataframe["date"].dt.hour
        return dataframe

    def set_freqai_targets(
        self,
        dataframe: DataFrame,
        metadata: dict,
        **kwargs,
    ) -> DataFrame:
        dataframe[TARGET_ZERO_COLUMN] = calculate_target_zero(
            dataframe,
            close_column="close",
            periods=self.freqai_info["feature_parameters"]["label_period_candles"],
        )
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        enter_long = (
            (dataframe["do_predict"] == 1)
            & dataframe["standard_long"]
            & (dataframe[TARGET_ZERO_COLUMN] > dataframe["target_roi"])
            & (dataframe["volume"] > 0)
        )
        enter_short = (
            (dataframe["do_predict"] == 1)
            & dataframe["standard_short"]
            & (dataframe[TARGET_ZERO_COLUMN] < dataframe["sell_roi"])
            & (dataframe["volume"] > 0)
        )

        dataframe.loc[enter_long, ["enter_long", "enter_tag"]] = (
            1,
            "hma_sqz_target_zero_long",
        )
        dataframe.loc[enter_short, ["enter_short", "enter_tag"]] = (
            1,
            "hma_sqz_target_zero_short",
        )
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        exit_long = (
            dataframe["standard_short"]
            | (
                (dataframe["do_predict"] == 1)
                & (dataframe[TARGET_ZERO_COLUMN] < dataframe["sell_roi"])
            )
        )
        exit_short = (
            dataframe["standard_long"]
            | (
                (dataframe["do_predict"] == 1)
                & (dataframe[TARGET_ZERO_COLUMN] > dataframe["target_roi"])
            )
        )

        dataframe.loc[exit_long, ["exit_long", "exit_tag"]] = (
            1,
            "hma_sqz_target_zero_exit_long",
        )
        dataframe.loc[exit_short, ["exit_short", "exit_tag"]] = (
            1,
            "hma_sqz_target_zero_exit_short",
        )
        return dataframe
