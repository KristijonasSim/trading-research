# Fear & Greed trendas (papers/48_fear_greed): laikyti BTC/ETH, kai Crypto Fear & Greed indeksas > 60.
# Indekso reikšmė su data D skelbiama D 00:00 UTC; dienos žvakė D uždaroma D+1 00:00 – signalas naudoja D reikšmę, įėjimas D+1 atidarymu.
# Duomenys: user_data/data/fng.json (backtestui); dry-run/live režime atnaujinama iš api.alternative.me kas 6 val.
import json, os, time, urllib.request
import pandas as pd
from freqtrade.strategy import IStrategy

API = "https://api.alternative.me/fng/?limit=0&format=json"


class FearGreedTrend(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "1d"
    can_short = False
    minimal_roi = {"0": 100}
    stoploss = -0.99
    startup_candle_count = 5
    TH = 60
    _cache = None
    _loaded = 0

    def _fng(self):
        path = os.path.join(self.config["user_data_dir"], "data", "fng.json")
        live = self.config.get("runmode").value in ("dry_run", "live")
        if live and time.time() - self._loaded > 6 * 3600:
            try:
                data = urllib.request.urlopen(API, timeout=20).read()
                json.loads(data); open(path, "wb").write(data)
            except Exception:
                pass
            self._cache = None
        if self._cache is None:
            d = json.load(open(path))["data"]
            s = pd.Series({pd.to_datetime(int(x["timestamp"]), unit="s", utc=True): int(x["value"]) for x in d}).sort_index()
            self._cache = s[~s.index.duplicated()]; self._loaded = time.time()
        return self._cache

    def populate_indicators(self, df, metadata):
        f = self._fng().rename("fng").rename_axis("date").reset_index()
        df = df.merge(f, on="date", how="left")
        df["fng"] = df["fng"].ffill()
        return df

    def populate_entry_trend(self, df, metadata):
        df.loc[df["fng"] > self.TH, "enter_long"] = 1
        return df

    def populate_exit_trend(self, df, metadata):
        df.loc[df["fng"] <= self.TH, "exit_long"] = 1
        return df
