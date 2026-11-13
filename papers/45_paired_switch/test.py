#!/usr/bin/env python3
"""#45 Paired Switching (Akhilesh Maewal 2017, SSRN; QuantConnect bibliotekos strategija): laikyti tą iš poros (SPY/TLT, QQQ/TLT, SPY/GLD),
kurio praėjusio laikotarpio (1 / 3 mėn.) grąža didesnė; perbalansavimas kas mėnesį/ketvirtį. Kaštai 0,05 %. 2005–2015 ir 2016–2026."""
import os, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__))
C = pd.read_csv(f"{H}/../../etf-rotation/data/close.csv", index_col=0, parse_dates=True)
R = C.pct_change().fillna(0)
def st(x, a, b):
    x = x[a:b]; e = (1 + x).cumprod(); y = len(x) / 252
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+.1f}%/m. DD {(e / e.cummax() - 1).min() * 100:.0f}%"
me = pd.Series(C.index, C.index).groupby(C.index.to_period("M")).last().values
for a, b in [("SPY", "TLT"), ("QQQ", "TLT"), ("SPY", "GLD"), ("QQQ", "IEF"), ("TQQQ", "TLT")]:
    print(f"{a} laikyti: 2005–15 {st(R[a], '2005', '2016')} | 2016–26 {st(R[a], '2016', '2027')}")
    for L, step in [(1, 1), (3, 3), (3, 1), (6, 1)]:
        w = pd.Series(np.nan, C.index)
        for i, d in enumerate(me):
            if i < L or i % step: continue
            p0 = me[i - L]; ra = C.at[d, a] / C.at[p0, a] - 1; rb = C.at[d, b] / C.at[p0, b] - 1
            if np.isnan(ra): continue
            w[d] = 1.0 if ra > rb or np.isnan(rb) else 0.0
        w = w.ffill().shift(1).fillna(1)
        x = w * R[a] + (1 - w) * R[b] - w.diff().abs().fillna(0) * 0.001
        print(f"  {a}/{b} L={L} mėn. kas {step}: 2005–15 {st(x, '2005', '2016')} | 2016–26 {st(x, '2016', '2027')}", flush=True)
