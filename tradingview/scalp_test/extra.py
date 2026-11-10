import sys, numpy as np, pandas as pd
from sim import load
from intraday import rth, noise, stats
D = sys.argv[1]
for name in ("NAS100", "SPX500", "US30"):
    ny = rth(load(D, name, "5min"))
    # Gao, Han, Li, Zhou (2018) intraday momentum: grąža vakar close -> 10:00 nusako paskutinį pusvalandį
    rows, pc = [], None
    for d, g in ny.groupby("day"):
        if pc is not None and len(g) >= 70:
            r1 = g.close[g.tod == 595]
            a = g.open[g.tod == 930]
            if len(r1) and len(a):
                side = 1 if r1.iloc[0] > pc else -1
                rows.append((pd.Timestamp(d), side, side * (g.close.iloc[-1] / a.iloc[0] - 1) - 0.0002))
        pc = g.close.iloc[-1]
    mom = pd.DataFrame(rows, columns=["day", "side", "ret"])
    print(name, "MOMENTUM", {k: v for k, v in stats(mom, "2021-03-01", "2026-11-10").items()})
    for fee in (0.00003, 0.0001, 0.0002):
        t = noise(ny, fee=fee)
        s1, s2 = stats(t, "2021-03-01", "2026-11-10"), stats(t, "2025-01-01", "2026-11-10")
        print(f"  NOISE fee {fee*100:.3f}%: visas {s1['cagr']}%/m dd {s1['dd']} pf {s1['pf']} | 2025+ {s2['cagr']}%/m pf {s2['pf']}")
