"""Larry Connors trumpalaikės strategijos (dienos žvakės, signalas uždarymu, sandoris tą pačią uždarymo kainą – kaip knygose;
konservatyviau: įėjimas kitos dienos uždarymu). 0,05 % į pusę. Grynieji = T-bill.
RSI2: pirkti, kai close > SMA200 ir RSI(2) < 10; parduoti, kai close > SMA5. (Short Term Trading Strategies That Work, 2009)
Double 7s: pirkti, kai close > SMA200 ir close = 7 d. minimumas; parduoti, kai close = 7 d. maksimumas. (Connors & Alvarez)
"""
import sys
import numpy as np
import pandas as pd
d = pd.read_pickle(sys.argv[1])["Close"]
cash = (d["^IRX"].ffill() / 100 / 252).fillna(0)


def rsi(s, n):
    x = s.diff(); u = x.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(); dn = (-x).clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + u / dn)


def sim(c, entry, exit_, lag=1, lev=1.0):
    pos = np.zeros(len(c)); p = 0
    for i in range(len(c)):
        if p == 0 and entry.iloc[i]: p = 1
        elif p == 1 and exit_.iloc[i]: p = 0
        pos[i] = p
    pos = pd.Series(pos, c.index).shift(lag).fillna(0) * lev
    r = c.pct_change().fillna(0)
    return pos * r + (1 - pos).clip(lower=0) * cash.reindex(c.index).fillna(0) - (pos - lev * 0 - pos.shift(1).fillna(0)).abs() * 0.0005 - (pos < 0) * 0 - (pos > 1) * (pos - 1) * cash.reindex(c.index).fillna(0) * 2, pos


def st(x, a, b):
    x = x[a:b]; eq = (1 + x).cumprod(); y = len(x) / 252
    return f"{100*(eq.iloc[-1]**(1/y)-1):5.1f}%/m krit.{100*(1-eq/eq.cummax()).max():3.0f}%"


P = [("2011-01-01", "2018-12-31"), ("2019-01-01", "2026-11-10"), ("2021-01-01", "2026-11-10")]
for t in ("SPY", "QQQ"):
    c = d[t].dropna()
    print(f"== {t}" + " " * 26 + " | ".join(f"{a[:4]}-{b[:4]}".ljust(19) for a, b in P))
    print(f"{'laikyti':32}" + " | ".join(st(c.pct_change().fillna(0), a, b).ljust(19) for a, b in P))
    s200, s5 = c.rolling(200).mean(), c.rolling(5).mean()
    r2 = rsi(c, 2)
    for lab, en, ex in [("RSI2", (c > s200) & (r2 < 10), c > s5),
                        ("Double 7s", (c > s200) & (c <= c.rolling(7).min()), c >= c.rolling(7).max())]:
        for lev in (1.0, 2.0):
            ret, pos = sim(c, en, ex, 1, lev)
            print(f"{lab + f' {lev:.0f}x':32}" + " | ".join(st(ret, a, b).ljust(19) for a, b in P) + f"  rinkoje {100*(pos['2011':]>0).mean():.0f}%")
