import sys, time, datetime as dt
from pathlib import Path
import dukascopy_python as d, dukascopy_python.instruments as i
out = Path(sys.argv[1])
SYMS = "AAPL AMD AMZN AVGO BAC BA CRM DIS GOOGL INTC JPM MSFT MU NFLX NVDA ORCL PLTR TSLA UBER XOM".split()
for s in SYMS:
    f = out / f"{s}.csv"
    if f.exists(): continue
    for k in range(5):
        try:
            df = d.to_dataframe(d.fetch_candles(getattr(i, f"I_{s}_US_USD"), 5, d.TimeUnit.MINUTE, d.OfferSide.BID,
                                                dt.datetime(2021, 1, 1), dt.datetime(2026, 11, 11)))
            df.to_csv(f); print(s, len(df), df.index[0], flush=True); break
        except Exception as e:
            print(s, "retry", k, repr(e)[:100], flush=True); time.sleep(20 * (k + 1))
