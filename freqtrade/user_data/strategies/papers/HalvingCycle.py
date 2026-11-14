# BTC halvingo ciklas (papers/81_halving_cycle): laikyti nuo 500 d. prieš halvingą iki 550 d. po jo (populiari Rekt Capital ir kt. taisyklė).
# Signalas priklauso tik nuo datos (halvingų datos žinomos iš anksto), todėl ateities duomenų nenaudoja.
import pandas as pd
from freqtrade.strategy import IStrategy

HALVINGS = pd.to_datetime(["2012-11-28", "2016-07-09", "2020-05-11", "2024-04-20", "2028-04-15"], utc=True)


class HalvingCycle(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "1d"
    can_short = False
    minimal_roi = {"0": 100}
    stoploss = -0.99
    startup_candle_count = 1
    BEFORE, AFTER = 500, 550

    def populate_indicators(self, df, metadata):
        inside = pd.Series(False, index=df.index)
        for h in HALVINGS:
            inside |= (df["date"] >= h - pd.Timedelta(days=self.BEFORE)) & (df["date"] < h + pd.Timedelta(days=self.AFTER))
        df["cycle"] = inside.astype(int)
        return df

    def populate_entry_trend(self, df, metadata):
        df.loc[df["cycle"] == 1, "enter_long"] = 1
        return df

    def populate_exit_trend(self, df, metadata):
        df.loc[df["cycle"] == 0, "exit_long"] = 1
        return df
