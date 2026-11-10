"""Connors RSI(2) iš karto daugeliui ETF: pirkti, kai close > SMA200 ir RSI(2) < 10; parduoti, kai close > SMA5.
Vienu metu iki K pozicijų, kiekviena 1/K kapitalo (jei signalų daugiau – žemiausias RSI pirmas). Įėjimas kitos dienos uždarymu.
0,05 % į pusę, grynieji = T-bill. Parametrai iš knygos, nederinti.
"""
import sys
import numpy as np
import pandas as pd
d = pd.read_pickle(sys.argv[1])["Close"].ffill()
cash = (d.pop("^IRX") / 100 / 252).fillna(0)
U = ["SPY", "QQQ", "IWM", "DIA", "XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB", "EFA", "EEM", "TLT", "GLD"]
C = d[U]
R = C.pct_change().fillna(0)
x = C.diff(); u = x.clip(lower=0).ewm(alpha=.5, adjust=False).mean(); dn = (-x).clip(lower=0).ewm(alpha=.5, adjust=False).mean()
RSI = 100 - 100 / (1 + u / dn)
S200, S5 = C.rolling(200).mean(), C.rolling(5).mean()


def run(univ, K, lev=1.0):
    held = set(); W = pd.DataFrame(0.0, C.index, univ)
    for i, dt in enumerate(C.index[200:], 200):
        for t in list(held):
            if C.at[dt, t] > S5.at[dt, t]:
                held.discard(t)
        cand = [t for t in univ if t not in held and C.at[dt, t] > S200.at[dt, t] and RSI.at[dt, t] < 10]
        for t in sorted(cand, key=lambda t: RSI.at[dt, t])[:max(0, K - len(held))]:
            held.add(t)
        for t in held:
            W.at[dt, t] = lev / K
    Wp = W.shift(1).fillna(0)  # sprendimas uždarymu -> pozicija nuo kitos dienos
    expo = Wp.sum(axis=1)
    ret = (Wp * R[univ]).sum(axis=1) + (1 - expo).clip(lower=0) * cash - (expo - 1).clip(lower=0) * cash - W.diff().abs().sum(axis=1).fillna(0) * 0.0005
    return ret, expo


def st(x, a, b):
    x = x[a:b]; eq = (1 + x).cumprod(); y = len(x) / 252
    return f"{100*(eq.iloc[-1]**(1/y)-1):5.1f}%/m krit.{100*(1-eq/eq.cummax()).max():3.0f}%"


P = [("2006-01-01", "2010-12-31"), ("2011-01-01", "2018-12-31"), ("2019-01-01", "2026-11-10"), ("2021-01-01", "2026-11-10")]
print(" " * 30 + " | ".join(f"{a[:4]}-{b[:4]}".ljust(19) for a, b in P))
print(f"{'laikyti SPY':30}" + " | ".join(st(R.SPY, a, b).ljust(19) for a, b in P))
for lab, univ, K, lev in [("4 indeksai, K=2", U[:4], 2, 1.0), ("17 ETF, K=4", U, 4, 1.0), ("17 ETF, K=4, 1.5x", U, 4, 1.5),
                          ("17 ETF, K=6", U, 6, 1.0), ("13 akcijų ETF, K=4", U[:13], 4, 1.0)]:
    r, e = run(univ, K, lev)
    print(f"{lab:30}" + " | ".join(st(r, a, b).ljust(19) for a, b in P) + f"  vid. pozicija {100*e['2006':].mean():.0f}%")
