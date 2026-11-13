"""Dual Thrust (Michael Chalek), tik long, BTC/ETH. Riba = dienos atidarymas (00 UTC) + K × max(HH−LC, HC−LL) per N ankstesnių dienų.
Įeinama 5m žvake, kai kaina pramuša ribą; uždaroma dienos gale (pirmoje naujos dienos žvakėje). Patikra: papers/18_turtle/."""
from datetime import timedelta
import numpy as np
import pandas as pd
from freqtrade.strategy import IStrategy, merge_informative_pair


class DualThrust(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "5m"
    can_short = False
    minimal_roi = {"0": 100}
    stoploss = -0.99
    use_exit_signal = True
    startup_candle_count = 2000
    N, K = 4, 0.7

    def informative_pairs(self):
        return [(p, "1d") for p in self.dp.current_whitelist()]

    def populate_indicators(self, df: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        d = self.dp.get_pair_dataframe(metadata["pair"], "1d").copy()
        hh = d["high"].rolling(self.N).max(); ll = d["low"].rolling(self.N).min()
        hc = d["close"].rolling(self.N).max(); lc = d["close"].rolling(self.N).min()
        d["rng"] = np.maximum(hh - lc, hc - ll)          # baigtų dienų diapazonas
        d["day"] = d["date"] + timedelta(days=1)          # galioja KITĄ dieną
        df["day"] = df["date"].dt.floor("D")
        df = df.merge(d[["day", "rng"]], on="day", how="left")
        df["day_open"] = df.groupby("day")["open"].transform("first")
        df["up"] = df["day_open"] + self.K * df["rng"]
        return df

    def populate_entry_trend(self, df, metadata):
        df.loc[df["high"] > df["up"], "enter_long"] = 1
        return df

    def populate_exit_trend(self, df, metadata):
        df["exit_long"] = 0
        return df

    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        if current_time.date() > trade.open_date_utc.date():
            return "day_end"
        return None
