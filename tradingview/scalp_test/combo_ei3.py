"""Noise Breakout NAS100 (3x) ir EI3v2 (alts10, freqtrade 5m) mėnesinių grąžų koreliacija ir 50/50 portfelis (kas mėn. perbalansuojama), 2021-11 – 2026-11."""
import sys, glob, json, zipfile, numpy as np, pandas as pd
from sim import load
from intraday import rth
import noise2
D = sys.argv[1]; Z = sys.argv[2]
ny = rth(load(D, "NAS100", "5min")); Dd, closes = noise2.prep(ny)
noise2.st = lambda t, a, b: t
t = noise2.run_cfg((Dd, closes, 1.0, 0, "paper", 60, False))["tr"]
nb = t.groupby(t.day.dt.to_period("M")).ret.apply(lambda r: (1 + 3 * r - 2 * 0.06 / 252).prod() - 1)
zf = zipfile.ZipFile(sorted(glob.glob(Z))[-1]); n = [x for x in zf.namelist() if x.endswith(".json") and "config" not in x][0]
tr = pd.DataFrame(list(json.load(zf.open(n))["strategy"].values())[0]["trades"]); tr["m"] = pd.to_datetime(tr.close_date).dt.tz_localize(None).dt.to_period("M")
pm = tr.groupby("m").profit_abs.sum(); bal = 1000 + pm.cumsum().shift(1).fillna(0); ei = pm / bal
M = pd.DataFrame({"NB3x": nb, "EI3v2": ei}).loc["2021-11":"2026-10"].fillna(0)
M["50/50"] = M.mean(axis=1)
print("koreliacija:", round(M.NB3x.corr(M.EI3v2), 2))
for c in M:
    e = (1 + M[c]).cumprod(); y = len(M) / 12
    yr = (1 + M[c]).groupby(M.index.year).prod() - 1
    print(f"{c:6s} {(e.iloc[-1] ** (1 / y) - 1) * 100:+.1f}%/m. mėn. kritimas {(e / e.cummax() - 1).min() * 100:.0f}% blogiausias mėn. {M[c].min() * 100:+.0f}% | " + " ".join(f"{k%100}:{v*100:+.0f}" for k, v in yr.items()))
