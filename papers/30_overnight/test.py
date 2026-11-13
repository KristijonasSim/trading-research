#!/usr/bin/env python3
"""#30 Nakties grąžos premija (Cooper, Cliff, Gulen 2008; Lou, Polk, Skouras 2019): laikyti ETF tik nakčiai
(pirkti uždarymu, parduoti kitą rytą atidarymu) prieš tik dienai. Kaštai vienai pusei 0 / 0,01 / 0,03 %.
Kūrimas 2005–2015, nematytas 2016–2026. Yahoo dienos open/close (pakoreguoti)."""
import os, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__))
C = pd.read_csv(f"{H}/../../etf-rotation/data/close.csv", index_col=0, parse_dates=True)
O = pd.read_csv(f"{H}/../../etf-rotation/data/open.csv", index_col=0, parse_dates=True)
def st(R, a, b):
    R = R[a:b].dropna(); e = (1 + R).cumprod(); y = len(R) / 252
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+.1f}%/m. DD {(e / e.cummax() - 1).min() * 100:.0f}%"
for t in ["SPY", "QQQ", "IWM", "TQQQ", "GLD", "TLT"]:
    on = O[t] / C[t].shift() - 1; day = C[t] / O[t] - 1; hold = C[t].pct_change()
    print(f"{t} laikyti: 2005–15 {st(hold, '2005', '2016')} | 2016–26 {st(hold, '2016', '2027')}")
    for cost in [0, 0.0001, 0.0003]:
        print(f"  naktis kaštai {cost*100:.2f}%: 2005–15 {st(on - 2*cost, '2005', '2016')} | 2016–26 {st(on - 2*cost, '2016', '2027')}   diena: 2016–26 {st(day - 2*cost, '2016', '2027')}")
