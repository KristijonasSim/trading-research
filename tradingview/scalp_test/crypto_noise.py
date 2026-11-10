import sys, pandas as pd
from noise3 import sess, run, st
import noise3
noise3.FEE = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0005
from sim import load
D = sys.argv[1]
for name in ("BTC", "ETH", "SOL"):
    x = sess(load(D, name, "5min"), "UTC", 0, 1440)
    c = x.groupby("day").close.last(); yrs = (c.index[-1] - c.index[0]).days / 365.25
    print(name, "laikyti %.1f%%/m" % (100 * ((c.iloc[-1] / c.iloc[0]) ** (1 / yrs) - 1)), "mokestis", noise3.FEE)
    for step in (60, 240):
        for lo in (False, True):
            t = run(x, 0, 1440, step, lo=lo)
            print(f"  kas {step} min {'tik long' if lo else 'long+short'}: 2023-24", st(t, "2023-01-01", "2025-01-01"), "| 2025-26", st(t, "2025-01-01", "2026-11-10"))
