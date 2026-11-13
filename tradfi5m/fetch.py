"""Dukascopy 5 min. žvakės: XAU (auksas), NAS100, SPX500, 2016-01 – 2026-11. Paleisti: ../quantconnect-lean/.venv/bin/python fetch.py"""
import time, datetime as dt
from pathlib import Path
import dukascopy_python as d, dukascopy_python.instruments as i
out = Path(__file__).parent / "raw"
INS = {"XAU": i.I_XAU_USD, "NAS100": i.I_USATECH_IDX_USD, "SPX500": i.I_USA500_IDX_USD}
for name, ins in INS.items():
    for y in range(2016, 2027):
        f = out / f"{name}_{y}.csv"
        if f.exists(): continue
        a = dt.datetime(y, 1, 1); b = min(dt.datetime(y + 1, 1, 1), dt.datetime(2026, 11, 12))
        for k in range(6):
            try:
                df = d.to_dataframe(d.fetch_candles(ins, 5, d.TimeUnit.MINUTE, d.OfferSide.BID, a, b))
                df.to_csv(f); print(name, y, len(df), flush=True); break
            except Exception as e:
                print(name, y, "retry", k, repr(e)[:100], flush=True); time.sleep(30 * (k + 1))
print("FETCH_DONE")
