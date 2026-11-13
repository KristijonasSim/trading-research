#!/usr/bin/env python3
"""#27 Trendo klasika III ant kripto (dienos, Binance spot, tik long, 0,1 % mokestis):
 - KAMA (Kaufman, „Smarter Trading“ 1995): long kai close > KAMA(10,2,30) ir KAMA kyla;
 - Supertrend (O. Seban): ATR(10) × 3;
 - Hull MA (A. Hull 2005): long kai HMA(n) kyla;
 - Chandelier exit (Le Beau): įėjimas 22 d. maksimumu, išėjimas max(high,22) − 3×ATR(22).
Pozicija pagal uždarymo signalą laikoma nuo kitos dienos (kripto atidarymas ≈ vakar uždarymas).
2018-01 – 2021-11 (nematytas) ir 2021-11 – 2026-11."""
import os, numpy as np, pandas as pd
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/binance_1d")
G = {"BTC+ETH": ["BTC", "ETH"], "alts10": ["XRP", "BNB", "SOL", "DOGE", "ADA", "TRX", "LINK", "AVAX", "LTC", "DOT"]}
FEE = 0.001
def load(s):
    d = pd.read_csv(f"{D}/{s}USDT.csv"); d.index = pd.to_datetime(d.t, unit="ms"); return d[["o", "h", "l", "c"]]
def atr(d, n):
    tr = pd.concat([d.h - d.l, (d.h - d.c.shift()).abs(), (d.l - d.c.shift()).abs()], axis=1).max(axis=1); return tr.ewm(alpha=1/n, adjust=False).mean()
def kama(c, n=10, f=2, s=30):
    er = (c - c.shift(n)).abs() / c.diff().abs().rolling(n).sum()
    sc = (er * (2/(f+1) - 2/(s+1)) + 2/(s+1)) ** 2
    k = np.full(len(c), np.nan); v = c.values; scv = sc.values
    for i in range(n, len(c)):
        k[i] = v[i] if np.isnan(k[i-1]) else k[i-1] + scv[i] * (v[i] - k[i-1])
    return pd.Series(k, c.index)
def wma(x, n): w = np.arange(1, n+1); return x.rolling(n).apply(lambda a: (a*w).sum()/w.sum(), raw=True)
def hma(c, n): return wma(2*wma(c, n//2) - wma(c, n), int(np.sqrt(n)))
def supertrend(d, n=10, m=3):
    a = atr(d, n); hl2 = (d.h + d.l) / 2; up = (hl2 - m*a).values; dn = (hl2 + m*a).values; c = d.c.values
    fu, fd, trend = up.copy(), dn.copy(), np.ones(len(d))
    for i in range(1, len(d)):
        fu[i] = max(up[i], fu[i-1]) if c[i-1] > fu[i-1] else up[i]
        fd[i] = min(dn[i], fd[i-1]) if c[i-1] < fd[i-1] else dn[i]
        trend[i] = 1 if c[i] > fd[i-1] else (0 if c[i] < fu[i-1] else trend[i-1])
    return pd.Series(trend, d.index)
def chandelier(d, n=22, m=3):
    a = atr(d, n); hh = d.h.rolling(n).max(); pos = np.zeros(len(d)); c = d.c.values
    for i in range(n+1, len(d)):
        if pos[i-1] == 0: pos[i] = 1 if c[i] >= hh.iloc[i-1] else 0
        else: pos[i] = 0 if c[i] < hh.iloc[i] - m*a.iloc[i] else 1
    return pd.Series(pos, d.index)
def strat(d, name, p):
    c = d.c
    if name == "KAMA": k = kama(c, p); return ((c > k) & (k > k.shift())).astype(float)
    if name == "Supertrend": return supertrend(d, 10, p)
    if name == "HMA": h = hma(c, p); return (h > h.shift()).astype(float)
    if name == "Chandelier": return chandelier(d, 22, p)
def ret(d, pos):
    p = pos.shift(1).fillna(0); return p * d.c.pct_change().fillna(0) - p.diff().abs().fillna(0) * FEE
def st(R, a, b):
    R = R[a:b]; e = (1 + R).cumprod(); y = len(R) / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+.1f}%/m. DD {(e / e.cummax() - 1).min() * 100:.0f}%"
data = {s: load(s) for g in G.values() for s in g}
for g, syms in G.items():
    hold = pd.concat([data[s].c.pct_change() for s in syms], axis=1, sort=True)["2018":].fillna(0).mean(axis=1)
    print(f"{g} laikyti: {st(hold, '2018-01-01', '2021-11-08')} | {st(hold, '2021-11-08', '2026-11-09')}")
    for name, ps in [("KAMA", [10, 20]), ("Supertrend", [2, 3, 4]), ("HMA", [20, 50, 100]), ("Chandelier", [2.5, 3, 4])]:
        for p in ps:
            pos = {s: strat(data[s], name, p) for s in syms}
            R = pd.concat([ret(data[s], pos[s]) for s in syms], axis=1, sort=True)["2018":].fillna(0).mean(axis=1)
            n = int(sum((pos[s].diff() == 1)["2021-11-08":].sum() for s in syms))
            y = (1 + R["2021-11-08":]).groupby(R["2021-11-08":].index.year).prod() - 1
            print(f"{g} {name}({p}): {st(R, '2018-01-01', '2021-11-08')} | {st(R, '2021-11-08', '2026-11-09')} | sand. 2021–26 {n} | " + " ".join(f"{k}:{v*100:+.0f}" for k, v in y.items()), flush=True)
