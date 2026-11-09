"""Dukascopy 15m BID candles 2017..2026-11-09 -> data/<name>_15m.csv.
Downloads year by year (resumable: data/parts/<name>_<year>.csv) and one instrument at a time,
because parallel requests get HTTP 429 (rate limit)."""
import sys, time, datetime as dt
from pathlib import Path
import pandas as pd
import dukascopy_python as d, dukascopy_python.instruments as i
INSTR = {"NAS100": "I_USATECH_IDX_USD", "US30": "I_USA30_IDX_USD", "SPX500": "I_USA500_IDX_USD",
         "GER40": "I_DEU_IDX_EUR", "XAUUSD": "I_XAU_USD"}
parts = Path("data/parts"); parts.mkdir(parents=True, exist_ok=True)
for name in sys.argv[1:] or INSTR:
    for y in range(2017, 2027):
        f = parts / f"{name}_{y}.csv"
        if f.exists(): continue
        for attempt in range(6):
            try:
                df = d.to_dataframe(d.fetch_candles(getattr(i, INSTR[name]), 15, d.TimeUnit.MINUTE, d.OfferSide.BID,
                                    dt.datetime(y, 1, 1), min(dt.datetime(y + 1, 1, 1), dt.datetime(2026, 11, 9))))
                df.to_csv(f); print(name, y, len(df), flush=True); break
            except Exception as e:
                print(name, y, "retry", attempt, e.__class__.__name__, flush=True); time.sleep(60 * (attempt + 1))
        time.sleep(5)
    fs = sorted(parts.glob(f"{name}_*.csv"))
    if len(fs) == 10:
        df = pd.concat(pd.read_csv(x, index_col=0, parse_dates=True) for x in fs)
        df[~df.index.duplicated()].sort_index().to_csv(f"data/{name}_15m.csv"); print(name, "DONE", len(df), flush=True)
