"""Dukascopy 1h BID candles 2021-10-01..2026-11-09 -> raw/hour/<T>.csv (US stocks/ETFs + forex)."""
import sys, pathlib, datetime as dt
import dukascopy_python as d, dukascopy_python.instruments as i
out = pathlib.Path(sys.argv[2]); ok, bad = [], []
for t in open(sys.argv[1]).read().split():
    if (out / f"{t}.csv").exists(): ok.append(t); continue
    if len(t) == 6 and t.isalpha() and t[:3] in ("EUR","GBP","USD","AUD","NZD","CAD","CHF","JPY"):
        name = f"I_{t[:3]}_{t[3:]}"
    else:
        name = f"I_{t.replace('.', '')}_US_USD"
    ins = getattr(i, name, None)
    if ins is None: bad.append(t); continue
    try:
        df = d.to_dataframe(d.fetch_candles(ins, 1, d.TimeUnit.HOUR, d.OfferSide.BID,
                            dt.datetime(2021, 10, 1), dt.datetime(2026, 11, 9)))
        df.to_csv(out / f"{t}.csv"); ok.append(t)
    except Exception as e:
        bad.append(f"{t}({e.__class__.__name__})")
print("OK", len(ok), " ".join(ok)); print("MISSING", len(bad), " ".join(bad))
