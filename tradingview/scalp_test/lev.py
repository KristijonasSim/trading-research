"""Noise Breakout NAS100 su svertu: pastovus 1–4x ir autorių dinaminis (tikslas 2 %/d. svyravimas, iki 4x; Zarattini ir kt. 2024).
Sverto kaina: 6 %/m. nuo skolintos dalies tik prekybos dienomis su pozicija (intraday – realiai CFD/ateities sandoriai)."""
import sys, numpy as np, pandas as pd
from sim import load
from intraday import rth
import noise2
D = sys.argv[1]; SPR = float(sys.argv[2]) if len(sys.argv) > 2 else None
ny = rth(load(D, "NAS100", "5min"))
Dd, closes = noise2.prep(ny)
orig = noise2.st; noise2.st = lambda t, a, b: t
r = noise2.run_cfg((Dd, closes, 1.0, 0, "paper", 60, False)); noise2.st = orig
t = r["tr"]; vol = closes.pct_change().rolling(14).std().shift(1); vol.index = pd.to_datetime(vol.index)
P = (("2016-01-01", "2021-03-01"), ("2021-03-01", "2025-01-01"), ("2025-01-01", "2026-11-15"))
def show(lab, tt):
    out = []
    for a, b in P:
        s = orig(tt, a, b); out.append(f"{a[:4]}–{b[2:4]}: {s['cagr']:+6.1f}%/m. DD {s['dd']:4.1f}%")
    y = tt.groupby(tt.day.dt.year).ret.apply(lambda x: (1 + x).prod() - 1)
    print(f"{lab:26s} " + " | ".join(out) + " | " + " ".join(f"{k%100}:{v*100:+.0f}" for k, v in y.items()), flush=True)
for L in (1, 2, 3, 4):
    tt = t.copy(); tt["ret"] = t.ret * L - (L - 1) * 0.06 / 252; show(f"{L}x pastovus", tt)
for tv, cap in ((0.02, 4), (0.015, 4), (0.02, 3)):
    s = (tv / vol.reindex(t.day).values).clip(0, cap)
    tt = t.copy(); tt["ret"] = t.ret.values * s - (np.maximum(s, 1) - 1) * 0.06 / 252; show(f"dinaminis {tv*100:.1f}% iki {cap}x", tt)
print("vid. sandorių per metus:", round(len(t) / ((t.day.max() - t.day.min()).days / 365.25)))
