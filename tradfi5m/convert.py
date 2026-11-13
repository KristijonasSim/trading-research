"""Dukascopy 5 min. CSV -> freqtrade futures failai. Kiekvienas instrumentas atskirame datadir,
įrašomas kaip ADA/USDT:USDT ir BTC/USDT:USDT (EI3v2 naudoja BTC kaip rinkos filtrą -> čia filtras = pats instrumentas).
Kaina perskaičiuojama, kad pradžioje būtų ~10 (grąžos nesikeičia). Finansavimo mokestis = 0."""
from pathlib import Path
import pandas as pd
R = Path(__file__).parent
for name in ["XAU", "NAS100", "SPX500"]:
    fs = sorted((R / "raw").glob(f"{name}_*.csv"))
    df = pd.concat(pd.read_csv(f, index_col=0, parse_dates=True) for f in fs)
    df = df[~df.index.duplicated()].sort_index()[["open", "high", "low", "close", "volume"]]
    df.index = pd.to_datetime(df.index, utc=True)
    k = 10 / df.close.iloc[0]
    for c in ["open", "high", "low", "close"]: df[c] *= k
    df["volume"] = df["volume"].clip(lower=1e-9) * 1e6
    out = R / f"ft_{name}" / "binance" / "futures"; out.mkdir(parents=True, exist_ok=True)
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    for tf, rule in [("5m", None), ("15m", "15min"), ("1h", "1h")]:
        d = df if rule is None else df.resample(rule).agg(agg).dropna()
        d = d.reset_index().rename(columns={d.index.name or "index": "date"})
        d.columns = ["date", "open", "high", "low", "close", "volume"]
        for p in ["ADA", "BTC"]:
            d.to_feather(out / f"{p}_USDT_USDT-{tf}-futures.feather")
            if tf == "1h":
                d.to_feather(out / f"{p}_USDT_USDT-1h-mark.feather")
                fr = d.copy(); fr[["open", "high", "low", "close"]] = 0.0; fr["volume"] = 0.0
                fr.to_feather(out / f"{p}_USDT_USDT-1h-funding_rate.feather")
    print(name, df.index[0], df.index[-1], len(df))
