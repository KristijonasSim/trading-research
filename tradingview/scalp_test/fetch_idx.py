import sys, time, datetime as dt
from pathlib import Path
import pandas as pd
import dukascopy_python as d, dukascopy_python.instruments as i
out = Path(sys.argv[1]); out.mkdir(exist_ok=True)
NAMES = {"NAS100": "I_USATECH_IDX_USD", "SPX500": "I_USA500_IDX_USD", "US30": "I_USA30_IDX_USD"}
for name, ins in NAMES.items():
    for y in range(2021, 2027):
        f = out / f"{name}_{y}.csv"
        if f.exists(): continue
        a = dt.datetime(y, 1, 1); b = min(dt.datetime(y + 1, 1, 1), dt.datetime(2026, 11, 10))
        for k in range(6):
            try:
                df = d.to_dataframe(d.fetch_candles(getattr(i, ins), 5, d.TimeUnit.MINUTE, d.OfferSide.BID, a, b))
                df.to_csv(f); print(name, y, len(df), flush=True); break
            except Exception as e:
                print(name, y, "retry", k, repr(e)[:100], flush=True); time.sleep(30 * (k + 1))
        time.sleep(2)
