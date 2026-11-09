"""Dukascopy 5m BID candles of the 1x ETFs behind 3x ETFs, 2021-09-01..2026-11-09 -> data/<ETF>_5m.csv.
Year by year, one at a time (parallel requests get HTTP 429). Resumable."""
import sys, time, datetime as dt
from pathlib import Path
import pandas as pd
import dukascopy_python as d, dukascopy_python.instruments as i
BASE = "QQQ SPY DIA IWM SMH XLK XLF XLE GDX GDXJ FXI TLT XLV IYR XLU EEM KRE EWZ".split()
parts = Path("data/parts")
for t in sys.argv[1:] or BASE:
    for y in range(2021, 2027):
        f = parts / f"{t}_{y}.csv"
        if f.exists(): continue
        a = dt.datetime(2021, 9, 1) if y == 2021 else dt.datetime(y, 1, 1)
        b = min(dt.datetime(y + 1, 1, 1), dt.datetime(2026, 11, 9))
        for k in range(6):
            try:
                df = d.to_dataframe(d.fetch_candles(getattr(i, f"I_{t}_US_USD"), 5, d.TimeUnit.MINUTE, d.OfferSide.BID, a, b))
                df.to_csv(f); print(t, y, len(df), flush=True); break
            except Exception as e:
                print(t, y, "retry", k, e.__class__.__name__, flush=True); time.sleep(60 * (k + 1))
        time.sleep(3)
    fs = sorted(parts.glob(f"{t}_*.csv"))
    if len(fs) == 6:
        df = pd.concat(pd.read_csv(x, index_col=0, parse_dates=True) for x in fs)
        df[~df.index.duplicated()].sort_index().to_csv(f"data/{t}_5m.csv"); print(t, "DONE", len(df), flush=True)
