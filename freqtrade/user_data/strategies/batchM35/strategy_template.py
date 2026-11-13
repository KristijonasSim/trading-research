"""
Freqtrade strategy scaffold — a known-good IStrategy skeleton.

Copy this, rename the class (PascalCase), and fill the three populate_* methods.
Run scripts/validate_strategy.py on the result before backtesting.

Indicators use `talib.abstract`. That won't execute in Claude's sandbox
(no TA-Lib C library), but it is the right import for your own machine where
`freqtrade backtesting` runs. If you want indicators that also run offline
for a quick smoke test, compute them in pandas instead (see references/strategy.md).
"""
from freqtrade.strategy import IStrategy
import talib.abstract as ta
import pandas as pd


class TemplateStrategy(IStrategy):
    # --- required-ish class attributes ---
    timeframe = "5m"
    stoploss = -0.10                       # must be negative
    minimal_roi = {"0": 0.10, "30": 0.05, "120": 0.02}

    # --- optional but common ---
    trailing_stop = False
    process_only_new_candles = True
    startup_candle_count = 30              # >= the largest indicator lookback

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["sma_20"] = ta.SMA(dataframe, timeperiod=20)
        return dataframe

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        dataframe.loc[
            (dataframe["rsi"] < 30) & (dataframe["close"] > dataframe["sma_20"]),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        dataframe.loc[
            (dataframe["rsi"] > 70),
            "exit_long",
        ] = 1
        return dataframe
