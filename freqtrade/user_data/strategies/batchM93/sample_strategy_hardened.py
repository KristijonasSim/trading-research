# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
from typing import Optional

from pandas import DataFrame

import talib.abstract as ta
from technical import qtpylib

from freqtrade.strategy import IStrategy, IntParameter


class SampleStrategyHardened(IStrategy):
    """
    Hardened sample strategy template.

    Differences vs. the plain sample:
    - More conservative default risk parameters.
    - Includes strategy-level protections (Cooldown, StoplossGuard, MaxDrawdown, LowProfitPairs).
    - Intended as a starting point for validation in dry-run/backtesting, NOT as a profitable
      or "ready for live trading" strategy.

    IMPORTANT: Backtest protections with: --enable-protections
    Tune all parameters (including protections) to your market, timeframe, and strategy behavior.
    """

    INTERFACE_VERSION = 3
    can_short: bool = False

    # Conservative defaults (can be overridden by config where applicable)
    timeframe = "5m"
    stoploss = -0.03
    minimal_roi = {
        "0": 0.03,
        "30": 0.015,
        "60": 0.005,
        "120": 0,
    }

    trailing_stop = False
    process_only_new_candles = True

    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    startup_candle_count: int = 200

    # Hyperoptable parameters (kept simple)
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
        """
        Strategy-level safeguards to reduce damage during adverse conditions.
        These MUST be tuned and validated (including --enable-protections in backtests).
        """
        return [
            {
                "method": "CooldownPeriod",
                "stop_duration_candles": 2,
            },
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 24,
                "trade_limit": 3,
                "stop_duration_candles": 4,
                "only_per_pair": False,
                "only_per_side": False,
            },
            {
                "method": "MaxDrawdown",
                "calculation_mode": "equity",
                "lookback_period_candles": 48,
                "trade_limit": 10,
                "stop_duration_candles": 12,
                "max_allowed_drawdown": 0.10,
            },
            {
                "method": "LowProfitPairs",
                "lookback_period_candles": 12,
                "trade_limit": 2,
                "stop_duration_candles": 6,
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
