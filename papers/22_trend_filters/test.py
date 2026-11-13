#!/usr/bin/env python3
"""#22 Paprasti žinomi trendo filtrai ant kripto (palyginimui): Faber 10 mėn. SMA (kas mėnesį), auksinis kryžius SMA50/200,
kaina > SMA200 (kasdien), kaina > SMA20 (kasdien). Tik long, pinigai kitaip. Mokestis 0,1 %, sandoris kitos dienos atidarymu."""
import os, numpy as np, pandas as pd
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/binance_1d")
G = {"BTC+ETH": ["BTC", "ETH"], "alts10": ["XRP", "BNB", "SOL", "DOGE", "ADA", "TRX", "LINK", "AVAX", "LTC", "DOT"]}
FEE = 0.001
def load(s):
    d = pd.read_csv(f"{D}/{s}USDT.csv"); d.index = pd.to_datetime(d.t, unit="ms"); return d[["o", "c"]]
def run(d, sig):
    pos = sig.shift(1).fillna(0)          # signalas uždarymu -> pozicija nuo kitos dienos
    r = d.c.pct_change().fillna(0)
    return pos * r - pos.diff().abs().fillna(0) * FEE
def faber(d):
    m = d.c.resample("ME").last(); s = (m > m.rolling(10).mean()).astype(float)
    return s.reindex(d.index, method="ffill").shift(0).fillna(0).where(d.index.is_month_end | True)
S = {"Faber 10 mėn. SMA": lambda d: (d.c.resample("ME").last() > d.c.resample("ME").last().rolling(10).mean()).astype(float).reindex(d.index).ffill().fillna(0),
     "Auksinis kryžius 50/200": lambda d: (d.c.rolling(50).mean() > d.c.rolling(200).mean()).astype(float),
     "Kaina > SMA200": lambda d: (d.c > d.c.rolling(200).mean()).astype(float),
     "Kaina > SMA100": lambda d: (d.c > d.c.rolling(100).mean()).astype(float),
     "Kaina > SMA20": lambda d: (d.c > d.c.rolling(20).mean()).astype(float)}
def st(r, a, b):
    r = r[a:b]; eq = (1 + r).cumprod(); y = (r.index[-1] - r.index[0]).days / 365.25
    return f"{(eq.iloc[-1] ** (1 / y) - 1) * 100:+.1f} ({(eq / eq.cummax() - 1).min() * 100:.0f})"
rows = []
for g, cs in G.items():
    data = {s: load(s) for s in cs}
    for n, f in S.items():
        R = pd.concat({s: run(d, f(d)) for s, d in data.items()}, axis=1, sort=True)["2018":].fillna(0).mean(axis=1)
        y = (1 + R["2021-11-08":]).groupby(R["2021-11-08":].index.year).prod() - 1
        rows.append(f"| {g} | {n} | {st(R, '2018-01-01', '2021-11-08')} | {st(R, '2021-11-08', '2026-11-08')} | {' '.join(f'{a}:{b*100:+.0f}' for a, b in y.items())} |"); print(rows[-1])
open("REZULTATAI.txt", "w").write("| Grupė | Filtras | 2018–2021-11 %/m (kritimas) | 2021-11–2026-11 | metai |\n|---|---|---|---|---|\n" + "\n".join(rows) + "\n")
