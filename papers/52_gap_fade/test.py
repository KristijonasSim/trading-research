#!/usr/bin/env python3
"""#52 Atidarymo tarpo prekyba ETF (populiari „gap fade“ / „gap and go“; pvz., Plastun ir kt. 2019 „Price gap anomaly“):
jei atidarymas < vakar uždarymas × (1 − X) -> pirkti atidarymu, parduoti uždarymu (fade); atvirkščiai – short po kilimo tarpo (variante).
Taip pat „gap and go“ (prekiauti tarpo kryptimi). SPY, QQQ, IWM, kaštai 0,02 % ir 0,05 %/pusė. 2005–2015 ir 2016–2026."""
import os, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__))
C = pd.read_csv(f"{H}/../../etf-rotation/data/close.csv", index_col=0, parse_dates=True)
O = pd.read_csv(f"{H}/../../etf-rotation/data/open.csv", index_col=0, parse_dates=True)
def st(x, a, b):
    x = x[a:b].fillna(0); e = (1 + x).cumprod(); y = len(x) / 252
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+.1f}%/m. DD {(e / e.cummax() - 1).min() * 100:.0f}%"
for t in ["SPY", "QQQ", "IWM"]:
    gap = O[t] / C[t].shift() - 1; day = C[t] / O[t] - 1
    for X in [0.003, 0.005, 0.01]:
        for nm, sgn in [("fade", -1), ("go", 1)]:
            for side in ["long", "ls"]:
                pos = pd.Series(0.0, C.index)
                pos[gap < -X] = -sgn   # fade po kritimo = long, go po kritimo = short
                pos[gap > X] = sgn
                if side == "long": pos = pos.clip(lower=0)
                x = pos * day - pos.abs() * 2 * 0.0005
                if True: print(f"{t} gap>{X*100:.1f}% {nm:4s} {side:4s}: 0,02 %: 2005–15 {st(pos*day - pos.abs()*0.0004, '2005', '2016')} | 2016–26 {st(pos*day - pos.abs()*0.0004, '2016', '2027')} || 0,05 %: 2016–26 {st(x, '2016', '2027')} | sandorių/m. {int(pos['2016':].abs().sum()/10.8)}", flush=True)
