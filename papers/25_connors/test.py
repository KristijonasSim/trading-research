#!/usr/bin/env python3
"""#25 Larry Connors trumpalaikis atšokimas ant kripto (dienos, Binance spot, tik long, 0,1 % mokestis).
Šaltinis: Connors & Alvarez, „Short Term Trading Strategies That Work“ (2008), „ConnorsRSI“ (2012).
 A) RSI(2) < X ir close > SMA200 -> pirkti; parduoti close > SMA5.
 B) Kaupiamasis RSI(2) (2 d. suma) < 35 ir close > SMA200 -> pirkti; parduoti RSI(2) > 65.
 C) ConnorsRSI (RSI3 + serijos RSI2 + 100 d. grąžos procentilis)/3 < 10 ir close > SMA200; parduoti CRSI > 70.
 D) Dvigubas 7 d.: close = 7 d. minimumas ir > SMA200; parduoti close = 7 d. maksimumas.
Signalas dienos uždarymu, sandoris kitos dienos atidarymu. 2018-01 – 2021-11 ir 2021-11 – 2026-11."""
import os, numpy as np, pandas as pd
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/binance_1d")
G = {"BTC+ETH": ["BTC", "ETH"], "alts10": ["XRP", "BNB", "SOL", "DOGE", "ADA", "TRX", "LINK", "AVAX", "LTC", "DOT"]}
FEE = 0.001
def load(s):
    d = pd.read_csv(f"{D}/{s}USDT.csv"); d.index = pd.to_datetime(d.t, unit="ms"); return d[["o", "h", "l", "c"]]
def rsi(x, n):
    dlt = x.diff(); up = dlt.clip(lower=0).ewm(alpha=1/n, adjust=False).mean(); dn = (-dlt.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)
def streak(c):
    s = np.zeros(len(c)); v = c.values
    for i in range(1, len(v)):
        if v[i] > v[i-1]: s[i] = s[i-1] + 1 if s[i-1] > 0 else 1
        elif v[i] < v[i-1]: s[i] = s[i-1] - 1 if s[i-1] < 0 else -1
    return pd.Series(s, c.index)
def signals(d, kind, x=10):
    c = d.c; sma200 = c.rolling(200).mean(); r2 = rsi(c, 2)
    if kind == "A": ent = (r2 < x) & (c > sma200); ex = c > c.rolling(5).mean()
    if kind == "B": ent = (r2 + r2.shift()) < x & (c > sma200) if False else ((r2 + r2.shift()) < x) & (c > sma200); ex = r2 > 65
    if kind == "C":
        crsi = (rsi(c, 3) + rsi(streak(c), 2) + c.pct_change().rolling(100).apply(lambda a: (a[:-1] < a[-1]).mean() * 100, raw=True)) / 3
        ent = (crsi < x) & (c > sma200); ex = crsi > 70
    if kind == "D": ent = (c <= c.rolling(7).min()) & (c > sma200); ex = c >= c.rolling(7).max()
    return ent, ex
def run(d, kind, x, trend=True):
    ent, ex = signals(d, kind, x)
    if not trend: pass
    r = np.zeros(len(d)); inpos = False; o = d.o.values; c = d.c.values; E = ent.values; X = ex.values; n = 0
    for i in range(201, len(d)):
        if inpos:
            r[i] = c[i] / c[i-1] - 1
            if X[i-1]:   # signalas vakar -> išeina šiandien atidarymu
                r[i] = o[i] / c[i-1] - 1 - FEE; inpos = False
        if not inpos and E[i-1] and not X[i-1]:
            r[i] = (1 + r[i]) * (c[i] / o[i] * (1 - FEE)) - 1; inpos = True; n += 1
    return pd.Series(r, d.index), n
def st(R, a, b):
    R = R[a:b]; e = (1 + R).cumprod(); y = len(R) / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+.1f}%/m. DD {(e / e.cummax() - 1).min() * 100:.0f}%"
data = {s: load(s) for g in G.values() for s in g}
rows = []
for g, syms in G.items():
    hold = pd.concat([data[s].c.pct_change() for s in syms], axis=1)["2018":].fillna(0).mean(axis=1)
    print(f"{g} laikyti: {st(hold, '2018-01-01', '2021-11-08')} | {st(hold, '2021-11-08', '2026-11-09')}")
    for kind, xs in [("A", [5, 10, 20]), ("B", [10, 35, 50]), ("C", [10, 15, 25]), ("D", [0])]:
        for x in xs:
            out = [run(data[s], kind, x) for s in syms]
            R = pd.concat([o[0] for o in out], axis=1)["2018":].fillna(0).mean(axis=1)
            y = (1 + R["2021-11-08":]).groupby(R["2021-11-08":].index.year).prod() - 1
            print(f"{g} {kind} x={x}: {st(R, '2018-01-01', '2021-11-08')} | {st(R, '2021-11-08', '2026-11-09')} | sandorių {sum(o[1] for o in out)} | " + " ".join(f"{k}:{v*100:+.0f}" for k, v in y.items()), flush=True)
