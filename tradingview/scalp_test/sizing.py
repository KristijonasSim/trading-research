"""Pozicijos dydis pagal svyravimą (Zarattini ir kt. 2024): dydis = min(cap, tikslas / 14 d. dienos svyravimas)."""
import sys, numpy as np, pandas as pd
from sim import load
from intraday import rth
import noise2
D = sys.argv[1]
ny = rth(load(D, "NAS100", "5min"))
Dd, closes = noise2.prep(ny)
# trades with per-day returns: re-run core loop capturing trades
res = []
orig = noise2.st
noise2.st = lambda t, a, b: t  # grąžina pačius sandorius
r = noise2.run_cfg((Dd, closes, 1.0, 0, "paper", 60, False))
noise2.st = orig
t = r["tr"]
dret = closes.pct_change()
vol = dret.rolling(14).std().shift(1)
vol.index = pd.to_datetime(vol.index)
def show(lab, tt):
    for a, b in (("2021-03-01", "2025-01-01"), ("2025-01-01", "2026-11-10")):
        print(f"  {lab:28} {a[:4]}-{b[:4]}", orig(tt, a, b))
show("1x (dabar)", t)
for tv in (0.01, 0.015, 0.02):
    for cap in (1, 2):
        s = (tv / vol.reindex(t.day).values).clip(0, cap)
        tt = t.copy(); tt["ret"] = t.ret.values * s
        show(f"tikslas {tv*100:.1f}% cap {cap}x", tt)
