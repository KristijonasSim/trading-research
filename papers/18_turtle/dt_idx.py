"""Dual Thrust ant indeksų/aukso (Yahoo dienos OHLC, tik long, įėjimas dienos viduje ties riba, išėjimas uždarymu), mokestis 0,02 %."""
import os, numpy as np, pandas as pd, yfinance as yf
f = "../13_volmanaged/data/ohlc.pkl"
if not os.path.exists(f):
    yf.download(["SPY", "QQQ", "GLD", "IWM"], start="2000-01-01", end="2026-11-13", auto_adjust=True, progress=False).to_pickle(f)
X = pd.read_pickle(f)
FEE = 0.0002
for s in ["SPY", "QQQ", "IWM", "GLD"]:
    d = pd.DataFrame({k: X[c][s] for k, c in zip("ohlc", ["Open", "High", "Low", "Close"])}).dropna()
    line = []
    for n, k in [(4, 0.5), (4, 0.7), (2, 0.5), (6, 0.6)]:
        rng = pd.concat([d.h.rolling(n).max() - d.c.rolling(n).min(), d.c.rolling(n).max() - d.l.rolling(n).min()], axis=1).max(axis=1).shift(1)
        up = d.o + k * rng; hit = d.h > up; px = np.maximum(d.o, up)
        r = pd.Series(np.where(hit, d.c / px - 1 - 2 * FEE, 0.0), d.index)
        def st(r, a, b):
            r = r[a:b]; eq = (1 + r).cumprod(); y = len(r) / 252
            return f"{(eq.iloc[-1] ** (1 / y) - 1) * 100:+.1f} ({(eq / eq.cummax() - 1).min() * 100:.0f})"
        line.append(f"n{n} k{k}: {st(r, '2005', '2015')} | {st(r, '2016', '2026')}")
    h = d.c.pct_change().fillna(0)
    print(f"{s}: laikyti {st(h, '2005', '2015')} | {st(h, '2016', '2026')};  " + ";  ".join(line), flush=True)
