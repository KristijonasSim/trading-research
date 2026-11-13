# Funding kontrarinis signalas (papers/32_funding_timing): long perp, kai 3 d. vidutinė dienos funding suma
# < 0,01 %/d. (žemiau neutralaus 0,03 %/d.), išeiti kai pakyla virš. Signalas dienos uždarymu, įėjimas kitos d. atidarymu.
import pandas as pd
from freqtrade.strategy import IStrategy
from freqtrade.enums import CandleType


class FundingContrarian(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "1d"
    can_short = False
    minimal_roi = {"0": 100}
    stoploss = -0.99
    startup_candle_count = 10
    process_only_new_candles = True
    N = 3
    TH = 0.0001

    def informative_pairs(self):   # gyvai (dry-run) atsisiųsti funding istoriją
        return [(p, "1h", CandleType.FUNDING_RATE) for p in self.dp.current_whitelist()]

    def populate_indicators(self, df, metadata):
        fr = self.dp.get_pair_dataframe(metadata["pair"], "1h", candle_type=CandleType.FUNDING_RATE)
        col = "open" if "open" in fr.columns else "funding_rate"
        f = fr[["date", col]].copy()
        f["day"] = f["date"].dt.floor("D")
        daily = f.groupby("day")[col].sum().rename("fsum").reset_index()   # dienos D mokėjimai 00, 08, 16 val.
        df = df.merge(daily, left_on="date", right_on="day", how="left").drop(columns="day")
        df["fmean"] = df["fsum"].rolling(self.N).mean()
        return df

    def populate_entry_trend(self, df, metadata):
        df.loc[df["fmean"] < self.TH, "enter_long"] = 1
        return df

    def populate_exit_trend(self, df, metadata):
        df.loc[df["fmean"] >= self.TH, "exit_long"] = 1
        return df
