"""Noise Breakout (Zarattini, Aziz, Barbon 2024) ant pavienių, labai judančių JAV akcijų (Dukascopy CFD 5m, 9:30–16:00 NY).
Tos pačios taisyklės kaip NAS100 (kas 60 min., stop max(riba, VWAP), uždaroma dienos pabaigoje).
Kaštai: 0,01 % ir 0,02 % į vieną pusę (komisinis + spread'as). Portfelis: lygiomis dalimis visose akcijose, 1x / 2x."""
import sys, numpy as np, pandas as pd
from sim import load
from intraday import rth
import noise2
D = sys.argv[1]; NAMES = sys.argv[2].split(",")
orig = noise2.st; noise2.st = lambda t, a, b: t
P = (("2021-03-01", "2025-01-01"), ("2025-01-01", "2026-11-15"))
def show(lab, tt):
    out = []
    for a, b in P:
        s = orig(tt, a, b); out.append(f"{a[:4]}–{b[2:4]}: {s['cagr']:+6.1f}%/m. DD {s['dd']:4.1f}%")
    y = tt.groupby(tt.day.dt.year).ret.apply(lambda x: (1 + x).prod() - 1)
    print(f"{lab:24s} " + " | ".join(out) + " | " + " ".join(f"{k%100}:{v*100:+.0f}" for k, v in y.items()), flush=True)
for fee in (0.0001, 0.0002):
    noise2.FEE = fee; daily = {}
    print(f"\n== kaštai {fee*100:.2f} % į pusę")
    for n in NAMES:
        ny = rth(load(D, n, "5min")); Dd, closes = noise2.prep(ny)
        for step in (60, 30):
            t = noise2.run_cfg((Dd, closes, 1.0, 0, "paper", step, False))["tr"]
            if step == 60: daily[n] = t.groupby("day").ret.sum()
            show(f"{n} kas {step} min", t)
    R = pd.DataFrame(daily).fillna(0)
    for L in (1, 2):
        pr = R.mean(axis=1) * L - (L - 1) * 0.06 / 252
        show(f"portfelis {len(NAMES)} akc. {L}x", pd.DataFrame({"day": pr.index, "ret": pr.values}))
