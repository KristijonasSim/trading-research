"""NAS100 1m candles from Dukascopy (BID), 2023-11-01 .. 2026-11-10, by quarter -> data/NAS100_1m_*.csv"""
import time, datetime as dt
from pathlib import Path
import dukascopy_python as d, dukascopy_python.instruments as i
out = Path(__file__).parent / "data"; out.mkdir(exist_ok=True)
a = dt.datetime(2023, 11, 1)
while a < dt.datetime(2026, 11, 10):
    b = min(dt.datetime(a.year + (a.month + 2) // 12, (a.month + 2) % 12 + 1, 1), dt.datetime(2026, 11, 10))
    f = out / f"NAS100_1m_{a:%Y%m}.csv"
    if not f.exists():
        for k in range(6):
            try:
                df = d.to_dataframe(d.fetch_candles(i.I_USATECH_IDX_USD, 1, d.TimeUnit.MINUTE, d.OfferSide.BID, a, b))
                df.to_csv(f); print(f.name, len(df), flush=True); break
            except Exception as e:
                print(f.name, "retry", k, repr(e)[:100], flush=True); time.sleep(20 * (k + 1))
    a = b
