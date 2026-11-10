import sys, numpy as np, pandas as pd
from sim import *
D = sys.argv[1]; name = sys.argv[2] if len(sys.argv) > 2 else "NAS100"
m = lambda s: np.datetime64(s, "m").astype(np.int64)
TR, TE, END = m("2021-03-01"), m("2025-01-01"), m("2026-11-10")
for tf in ("5min", "15min"):
    df = load(D, name, tf); x = indicators(df, 288)
    kauto = (x.medRange / 0.26).clip(0.05, 2).fillna(1).values
    print(tf, "bars", len(df), "k median", round(np.median(kauto), 2), "volume zero share", round((df.volume == 0).mean(), 3))
    for lab, k in [("auto", kauto), ("k=1", 1.0)]:
        b, s = signals(df, x, k)
        tr = simulate(df, b, s, k)
        print(f"  {lab:5} train", stats(tr, TR, TE), "\n        test ", stats(tr, TE, END))
    bh = df.close
    print("  laikyti: train %.1f%%/m, test %.1f%%/m" % tuple(100 * ((bh[(bh.index >= a)].iloc[0] and (bh[bh.index < b].iloc[-1] / bh[bh.index >= a].iloc[0]) ** (1 / ((b - a) / 525960)) - 1)) for a, b in [(pd.Timestamp("2021-03-01", tz="UTC"), pd.Timestamp("2025-01-01", tz="UTC")), (pd.Timestamp("2025-01-01", tz="UTC"), pd.Timestamp("2026-11-10", tz="UTC"))]))
