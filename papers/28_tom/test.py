#!/usr/bin/env python3
"""#28 Mėnesio sandūros efektas (Lakonishok, Smidt 1988; McConnell, Xu 2008): laikyti nuo paskutinės mėnesio
prekybos dienos iki 3-ios kito mėnesio dienos (−1…+3), kitu metu pinigai (BIL / 0). SPY, QQQ, TQQQ, IWM; kripto BTC+ETH.
Mokestis 0,05 % (ETF), 0,1 % (kripto). Kūrimas 2005–2015, nematytas 2016–2026."""
import os, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__))
C = pd.read_csv(f"{H}/../../etf-rotation/data/close.csv", index_col=0, parse_dates=True)
def tom_mask(idx, a=-1, b=3):
    s = pd.Series(idx, idx); m = idx.to_period("M")
    rank = s.groupby(m).cumcount() + 1; rev = s.groupby(m).cumcount(ascending=False) + 1
    # pozicija dieną t: grąža close(t-1)->close(t); laikome dienas, kurios yra paskutinės |a| mėnesio arba pirmos b
    return ((rev <= -a) | (rank <= b)).astype(float)
def st(R, a, b):
    R = R[a:b].dropna(); e = (1 + R).cumprod(); y = len(R) / 252
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+.1f}%/m. DD {(e / e.cummax() - 1).min() * 100:.0f}%"
for t in ["SPY", "QQQ", "IWM", "TQQQ"]:
    r = C[t].pct_change(); cash = C["BIL"].pct_change().fillna(0)
    for a, b in [(-1, 3), (-2, 3), (-1, 5), (-4, 3)]:
        # paskutinės |a| dienos: įeinama |a|-osios nuo galo dienos pradžioje (vakar uždarymu)
        pos = tom_mask(C.index, a, b)
        R = pos * r + (1 - pos) * cash - pos.diff().abs().fillna(0) * 0.0005
        print(f"{t} −{-a}…+{b}: 2005–15 {st(R, '2005', '2016')} | 2016–26 {st(R, '2016', '2027')} | laikyti {st(r, '2016', '2027')} | laiko dalis {pos.mean():.0%}")
# kripto (kalendorinės dienos)
D = f"{H}/../data/binance_1d"
for s in ["BTC", "ETH"]:
    d = pd.read_csv(f"{D}/{s}USDT.csv"); px = pd.Series(d.c.values, pd.to_datetime(d.t, unit="ms")); r = px.pct_change()
    for a, b in [(-1, 3), (-3, 3), (-1, 5)]:
        pos = tom_mask(px.index, a, b); R = pos * r - pos.diff().abs().fillna(0) * 0.001
        f = lambda R, x, y: (lambda e, n: f"{(e.iloc[-1] ** (365.25 / n) - 1) * 100:+.1f}%/m. DD {(e / e.cummax() - 1).min() * 100:.0f}%")((1 + R[x:y].fillna(0)).cumprod(), len(R[x:y]))
        print(f"{s} −{-a}…+{b}: 2018–21 {f(R, '2018', '2021-11-08')} | 2021–26 {f(R, '2021-11-08', '2027')}")
