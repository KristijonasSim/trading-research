"""Unseen-period check (2018-01-01..2021-11-08) for chosen strategies of a batch, same docker
sandbox as run_batch.py. Usage: BATCH=batch50g .venv/bin/python oos_batch.py Strat:group ..."""
import sys
import run_all as ra
import run_batch as rb

ra.TIMERANGE = "20180101-20211108"
_s = ra.summarize
ra.summarize = lambda d, s, m, g, timerange=ra.TIMERANGE: _s(d, s, m, g, timerange)
rb.OUT = ra.ROOT / "results" / f"oos_{rb.BATCH}"
for a in sys.argv[1:]:
    s, g = a.split(":")
    print(rb.run(s, g), flush=True)
