#!/usr/bin/env python3
"""
Convert downloaded prices into Lean's data folder (data/).
- equity daily  : Yahoo, dividend/split adjusted  -> data/equity/usa/daily/<t>.zip
- equity hour   : Dukascopy 1h, NY market hours, scaled by Yahoo's daily adjustment factor
                  so hourly and daily prices are on the same (dividend adjusted) basis
- forex daily/h : Dukascopy bid (ask = bid; costs come from the 0.1% fee model)
Prices are already adjusted, so factor files are flat (1.0).
"""
import shutil, zipfile
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
DATA = ROOT / "data"
LEAN = ROOT / "sources/lean-repo/Data"


def zwrite(path, inner, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(inner, "\n".join(lines) + "\n")


def px(v):
    return int(round(float(v) * 10000))


def main():
    for sub in ("market-hours", "symbol-properties"):
        shutil.copytree(LEAN / sub, DATA / sub, dirs_exist_ok=True)

    factors = {}
    for f in sorted((RAW / "daily").glob("*.csv")):
        t = f.stem.lower()
        df = pd.read_csv(f, index_col=0, parse_dates=True).dropna(subset=["Close"])
        factors[f.stem] = (df["Close"] / df["raw_close"]).to_dict()
        lines = [f"{d:%Y%m%d} 00:00,{px(r.Open)},{px(r.High)},{px(r.Low)},{px(r.Close)},{int(r.Volume)}"
                 for d, r in df.iterrows()]
        zwrite(DATA / f"equity/usa/daily/{t}.zip", f"{t}.csv", lines)
        first = df.index[0]
        (DATA / "equity/usa/map_files").mkdir(parents=True, exist_ok=True)
        (DATA / "equity/usa/factor_files").mkdir(parents=True, exist_ok=True)
        (DATA / f"equity/usa/map_files/{t}.csv").write_text(f"{first:%Y%m%d},{t},Q\n20501231,{t},Q\n")
        (DATA / f"equity/usa/factor_files/{t}.csv").write_text(f"{first:%Y%m%d},1,1,1\n20501231,1,1,1\n")

    for f in sorted((RAW / "hour").glob("*.csv")):
        t = f.stem
        df = pd.read_csv(f, index_col=0, parse_dates=True)
        if len(t) == 6 and t[:3] in ("EUR", "GBP", "USD", "AUD") and t not in factors:
            df.index = df.index.tz_convert("UTC").tz_localize(None)
            lines = [f"{d:%Y%m%d %H:%M},{r.open},{r.high},{r.low},{r.close},0,"
                     f"{r.open},{r.high},{r.low},{r.close},0" for d, r in df.iterrows()]
            zwrite(DATA / f"forex/oanda/hour/{t.lower()}.zip", f"{t.lower()}.csv", lines)
            continue
        if t not in factors:
            continue
        df.index = df.index.tz_convert("America/New_York").tz_localize(None)
        df = df[(df.index.hour >= 9) & (df.index.hour < 16) & (df.index.dayofweek < 5)]
        fac = factors[t]
        lines = []
        for d, r in df.iterrows():
            k = fac.get(pd.Timestamp(d.date()))
            if k is None:  # not a Yahoo trading day (holiday) -> skip
                continue
            lines.append(f"{d:%Y%m%d %H:%M},{px(r.open*k)},{px(r.high*k)},{px(r.low*k)},{px(r.close*k)},"
                         f"{int(r.volume*1000)}")
        zwrite(DATA / f"equity/usa/hour/{t.lower()}.zip", f"{t.lower()}.csv", lines)

    for f in sorted((RAW / "fxdaily").glob("*.csv")):
        t = f.stem.lower()
        df = pd.read_csv(f, index_col=0, parse_dates=True)
        df.index = df.index.tz_convert("UTC").tz_localize(None)
        lines = [f"{d:%Y%m%d} 00:00,{r.open},{r.high},{r.low},{r.close},0,{r.open},{r.high},{r.low},{r.close},0"
                 for d, r in df.iterrows()]
        zwrite(DATA / f"forex/oanda/daily/{t}.zip", f"{t}.csv", lines)
    print("equity daily", len(list((DATA / "equity/usa/daily").glob("*.zip"))),
          "equity hour", len(list((DATA / "equity/usa/hour").glob("*.zip"))),
          "fx hour", len(list((DATA / "forex/oanda/hour").glob("*.zip"))),
          "fx daily", len(list((DATA / "forex/oanda/daily").glob("*.zip"))))


if __name__ == "__main__":
    main()
