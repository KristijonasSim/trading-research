"""Aberration (Keith Fitschen, 1993): uždarymas > SMA35 + 2σ → pirkti; uždarymas < SMA35 → parduoti. Tik long, 1d. Patikra: papers/21_pruitt/."""
import pandas as pd
from freqtrade.strategy import IStrategy


class Aberration(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "1d"
    minimal_roi = {"0": 100}
    stoploss = -0.99
    startup_candle_count = 40

    def populate_indicators(self, df: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        df["m"] = df["close"].rolling(35).mean(); df["s"] = df["close"].rolling(35).std()
        return df

    def populate_entry_trend(self, df, metadata):
        df.loc[df["close"] > df["m"] + 2 * df["s"], "enter_long"] = 1
        return df

    def populate_exit_trend(self, df, metadata):
        df.loc[df["close"] < df["m"], "exit_long"] = 1
        return df
