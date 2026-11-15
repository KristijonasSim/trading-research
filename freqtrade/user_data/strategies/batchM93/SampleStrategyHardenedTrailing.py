# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
from typing import Optional

from pandas import DataFrame

import talib.abstract as ta
from technical import qtpylib

from freqtrade.strategy import IStrategy, IntParameter


class SampleStrategyHardenedTrailing(IStrategy):
    """
    Tuned hardened sample strategy + trailing stop (tuning iteration 2).

    Based on backtest analysis (2026-10-15..2026-11-14, OKX 5m, viral basket):
    - stop_loss exits were the main loss driver (avg ~-3.29% per hit)
    - ROI exits were frequent but small; market regime was strongly down
    Tuning intent (to be validated, not guaranteed better):
    - tighter default stoploss, faster/smaller ROI targets (config can override)
    - stricter protections to pause earlier during adverse sequences/drawdown
    - ENABLED trailing stop to lock in profits / tighten trailing loss
    """

    INTERFACE_VERSION = 3
    can_short: bool = False

    timeframe = "5m"
    stoploss = -0.025
    minimal_roi = {
        "0": 0.02,
        "20": 0.012,
        "45": 0.006,
        "90": 0,
    }

    trailing_stop = True
    trailing_stop_positive_offset = 0.01
    trailing_only_offset_is_reached = False
    process_only_new_candles = True

    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    startup_candle_count: int = 200

    buy_rsi = IntParameter(low=5, high=40, default=30, space="buy", optimize=True, load=True)
    sell_rsi = IntParameter(low=60, high=95, default=70, space="sell", optimize=True, load=True)
    short_rsi = IntParameter(low=60, high=95, default=70, space="sell", optimize=True, load=True)
    exit_short_rsi = IntParameter(low=5, high=40, default=30, space="exit", optimize=True, load=True)

    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }

    order_time_in_force = {"entry": "GTC", "exit": "GTC"}

    @property
    def protections(self):
        """Stricter safeguards (tune & validate per market/timeframe)."""
        return [
            {
                "method": "CooldownPeriod",
                "stop_duration_candles": 3,
            },
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 24,
                "trade_limit": 3,
                "stop_duration_candles": 8,
                "only_per_pair": False,
                "only_per_side": False,
            },
            {
                "method": "MaxDrawdown",
                "calculation_mode": "equity",
                "lookback_period_candles": 48,
                "trade_limit": 8,
                "stop_duration_candles": 12,
                "max_allowed_drawdown": 0.06,
            },
            {
                "method": "LowProfitPairs",
                "lookback_period_candles": 12,
                "trade_limit": 3,
                "stop_duration_candles": 8,
                "required_profit": 0.0,
            },
        ]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["adx"] = ta.ADX(dataframe)
        dataframe["rsi"] = ta.RSI(dataframe)

        macd = ta.MACD(dataframe)
        dataframe["macd"] = macd["macd"]
        dataframe["macdsignal"] = macd["macdsignal"]
        dataframe["macdhist"] = macd["macdhist"]

        dataframe["mfi"] = ta.MFI(dataframe)

        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe["bb_lowerband"] = bollinger["lower"]
        dataframe["bb_middleband"] = bollinger["mid"]
        dataframe["bb_upperband"] = bollinger["upper"]
        dataframe["bb_percent"] = (dataframe["close"] - dataframe["bb_lowerband"]) / (
            dataframe["bb_upperband"] - dataframe["bb_lowerband"]
        )
        dataframe["bb_width"] = (dataframe["bb_upperband"] - dataframe["bb_lowerband"]) / dataframe[
            "bb_middleband"
        ]

        dataframe["tema"] = ta.TEMA(dataframe, timeperiod=9)
        dataframe["sar"] = ta.SAR(dataframe)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (qtpylib.crossed_above(dataframe["rsi"], self.buy_rsi.value))
                & (dataframe["tema"] <= dataframe["bb_middleband"])
                & (dataframe["tema"] > dataframe["tema"].shift(1))
                & (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1

        dataframe.loc[
            (
                (qtpylib.crossed_above(dataframe["rsi"], self.short_rsi.value))
                & (dataframe["tema"] > dataframe["bb_middleband"])
                & (dataframe["tema"] < dataframe["tema"].shift(1))
                & (dataframe["volume"] > 0)
            ),
            "enter_short",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (qtpylib.crossed_above(dataframe["rsi"], self.sell_rsi.value))
                & (dataframe["tema"] > dataframe["bb_middleband"])
                & (dataframe["tema"] < dataframe["tema"].shift(1))
                & (dataframe["volume"] > 0)
            ),
            "exit_long",
        ] = 1

        dataframe.loc[
            (
                (qtpylib.crossed_above(dataframe["rsi"], self.exit_short_rsi.value))
                & (dataframe["tema"] <= dataframe["bb_middleband"])
                & (dataframe["tema"] > dataframe["tema"].shift(1))
                & (dataframe["volume"] > 0)
            ),
            "exit_short",
        ] = 1
        return dataframe
