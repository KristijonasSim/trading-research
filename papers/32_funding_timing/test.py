#!/usr/bin/env python3
"""#32 Funding rate kaip kontrarinis laiko signalas BTC/ETH (pvz., „funding rate extremes“ – Glassnode, Coinglass tyrimai;
Inan 2024 „Predictability of crypto returns: funding rates“). Signalas: N d. vidutinis funding.
 A) long kai funding < slenkstis (pesimizmas), kitu metu be pozicijos;
 B) long visada, išskyrus kai funding > aukštas slenkstis (perkaitimas);
 C) long-short: short kai funding labai didelis (perp, mokami/gauti funding įskaičiuoti).
Perp kainos papers/data/perp_1d, mokestis 0,05 %. Kūrimas 2020-01 – 2021-11, nematytas 2021-11 – 2026-11."""
import os, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__))
def load(s):
    f = pd.read_csv(f"{H}/../data/funding/{s}USDT.csv"); f = pd.Series(f.rate.values, pd.to_datetime(f.t, unit="ms")).resample("D").sum()
    p = pd.read_csv(f"{H}/../data/perp_1d/{s}USDT.csv"); p = pd.Series(p.c.values, pd.to_datetime(p.t, unit="ms"))
    df = pd.DataFrame({"c": p, "f": f}).dropna(); return df
def st(R, a, b):
    R = R[a:b]; e = (1 + R).cumprod(); y = len(R) / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+.1f}%/m. DD {(e / e.cummax() - 1).min() * 100:.0f}%"
data = {s: load(s) for s in ["BTC", "ETH"]}
def ret(df, pos):
    p = pos.shift(1).fillna(0); r = df.c.pct_change().fillna(0)
    return p * r - p * df.f - p.diff().abs().fillna(0) * 0.0005   # long moka funding (f>0), short gauna
hold = pd.concat([ret(d, pd.Series(1.0, d.index)) for d in data.values()], axis=1).mean(axis=1)
print(f"BTC+ETH perp laikyti: 2020–21 {st(hold, '2020-01-01', '2021-11-08')} | 2021–26 {st(hold, '2021-11-08', '2026-11-14')}")
for N in [1, 3, 7, 14]:
    for kind, th in [("A", 0.0), ("A", 0.0001), ("B", 0.0005), ("B", 0.001), ("C", 0.0005), ("C", 0.001)]:
        out = []
        for d in data.values():
            m = d.f.rolling(N).mean()   # dienos suma (3 mokėjimai)
            if kind == "A": pos = (m < th).astype(float)
            if kind == "B": pos = (m <= th).astype(float)
            if kind == "C": pos = pd.Series(np.where(m > th, -1.0, 1.0), d.index)
            out.append(ret(d, pos))
        R = pd.concat(out, axis=1).fillna(0).mean(axis=1)
        y = (1 + R["2021-11-08":]).groupby(R["2021-11-08":].index.year).prod() - 1
        print(f"N={N:2d} {kind} slenkstis {th*100:.2f}%/d.: 2020–21 {st(R, '2020-01-01', '2021-11-08')} | 2021–26 {st(R, '2021-11-08', '2026-11-14')} | " + " ".join(f"{k}:{v*100:+.0f}" for k, v in y.items()), flush=True)
