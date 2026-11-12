import sys, time, datetime as dt
from pathlib import Path
import dukascopy_python as d, dukascopy_python.instruments as i
out = Path(sys.argv[1])
for y in range(2016, 2027):
    f = out / f"NAS100_{y}.csv"
    if f.exists(): continue
    a = dt.datetime(y, 1, 1); b = min(dt.datetime(y + 1, 1, 1), dt.datetime(2026, 11, 11))
    for k in range(6):
        try:
            df = d.to_dataframe(d.fetch_candles(i.I_USATECH_IDX_USD, 1, d.TimeUnit.MINUTE, d.OfferSide.BID, a, b))
            df.to_csv(f); print(y, len(df), flush=True); break
        except Exception as e:
            print(y, "retry", k, repr(e)[:100], flush=True); time.sleep(30 * (k + 1))
