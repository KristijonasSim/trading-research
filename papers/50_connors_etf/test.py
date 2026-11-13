#!/usr/bin/env python3
"""#50 Connors RSI(2) ant ETF (originali rinka; Connors & Alvarez 2008): pirkti uždarymu kai RSI(2) < X ir close > SMA200, parduoti kai close > SMA5.
Variantai: kaupiamasis RSI(2) < 35 (2 d.), išėjimas RSI(2) > 65. SPY, QQQ, IWM; laisvi pinigai BIL. Įėjimas tos dienos uždarymu (MOC orderis – originalas)
ir konservatyviai kitos d. atidarymu. Kaštai 0,05 %. 2005–2015 ir 2016–2026."""
import os, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__))
C = pd.read_csv(f"{H}/../../etf-rotation/data/close.csv", index_col=0, parse_dates=True)
O = pd.read_csv(f"{H}/../../etf-rotation/data/open.csv", index_col=0, parse_dates=True)
def rsi(x, n):
    d = x.diff(); u = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean(); v = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean(); return 100 - 100/(1 + u/v)
def st(x, a, b):
    x = x[a:b].dropna(); e = (1 + x).cumprod(); y = len(x) / 252
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+.1f}%/m. DD {(e / e.cummax() - 1).min() * 100:.0f}%"
cash = C["BIL"].pct_change().fillna(0)
for t in ["SPY", "QQQ", "IWM"]:
    c, o = C[t], O[t]; r2 = rsi(c, 2); s200 = c.rolling(200).mean(); s5 = c.rolling(5).mean()
    print(f"{t} laikyti: 2005–15 {st(c.pct_change(), '2005', '2016')} | 2016–26 {st(c.pct_change(), '2016', '2027')}")
    for nm, ent, ex in [("RSI2<5", (r2 < 5) & (c > s200), c > s5), ("RSI2<10", (r2 < 10) & (c > s200), c > s5),
                        ("kaup.RSI2<35", (r2 + r2.shift() < 35) & (c > s200), r2 > 65)]:
        pos = np.zeros(len(c)); inp = False
        for i in range(len(c)):
            if inp and ex.iloc[i]: inp = False
            elif not inp and ent.iloc[i]: inp = True
            pos[i] = inp
        pos = pd.Series(pos, c.index)
        # MOC: pozicija nustatoma uždarymu, grąža nuo šio uždarymo iki kito
        p1 = pos.shift(1).fillna(0); x1 = p1 * c.pct_change().fillna(0) + (1 - p1) * cash - pos.diff().abs().fillna(0) * 0.0005
        # kitos d. atidarymas: įeinama/išeinama atidarymu
        p2 = pos.shift(1).fillna(0); prev = p2.shift(1).fillna(0)
        x2 = np.where((prev == 1) & (p2 == 1), c / c.shift(), np.where((prev == 0) & (p2 == 1), c / o, np.where((prev == 1) & (p2 == 0), o / c.shift(), 1))) - 1
        x2 = pd.Series(x2, c.index).fillna(0) + (1 - p2) * cash - p2.diff().abs().fillna(0) * 0.0005
        print(f"  {nm} MOC: 2005–15 {st(x1, '2005', '2016')} | 2016–26 {st(x1, '2016', '2027')} || atidarymu: 2016–26 {st(x2, '2016', '2027')} | rinkoje {pos['2016':].mean():.0%}", flush=True)
