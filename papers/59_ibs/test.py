"""59: IBS (Internal Bar Strength) atšokimas (Pagonidis 2013, „The IBS Effect“). IBS = (C − L) / (H − L).
Taisyklės: pirkti uždarymu, kai IBS < x; parduoti uždarymu, kai IBS > y (arba po 1 d.). Variantas su SMA200 filtru.
Vykdymas: A) tos dienos uždarymu (MOC, kaip originale), B) konservatyviai kitos dienos atidarymu. Kaštai 0,03 %/sandorį; laisvi pinigai – BIL.
Kūrimo laikotarpis iki 2012, nematytas 2013–2026. Paleisti: quantconnect-lean/.venv/bin/python papers/59_ibs/test.py"""
import os, numpy as np, pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); FEE = 0.0003
L = lambda t: pd.read_csv(f"{D}/data/{t}.csv", index_col=0, parse_dates=True)
bil = L("BIL").Close.pct_change()
def st(x, a, b):
    x = x[a:b].dropna(); e = (1 + x).cumprod(); y = len(x) / 252
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+5.1f}% kr {(e / e.cummax() - 1).min() * 100:3.0f}%"
PER = [("2001", "2012"), ("2013", "2019"), ("2020", "2026")]
print("periodai: 2001–12 | 2013–19 | 2020–26")
for t in ("SPY", "QQQ", "IWM", "DIA", "EFA", "TLT", "GLD"):
    d = L(t); c, o, h, l = d.Close, d.Open, d.High, d.Low
    ibs = ((c - l) / (h - l)).fillna(0.5); s200 = c.rolling(200).mean()
    cash = bil.reindex(c.index).fillna(0)
    print(f"\n{t} laikyti: " + " | ".join(st(c.pct_change(), a, b) for a, b in PER))
    for nm, ent, ex in [("IBS<0,2 → >0,8", ibs < 0.2, ibs > 0.8), ("IBS<0,2 → 1 d.", ibs < 0.2, None),
                        ("IBS<0,25 → >0,75", ibs < 0.25, ibs > 0.75), ("IBS<0,2 ir >SMA200 → >0,8", (ibs < 0.2) & (c > s200), ibs > 0.8),
                        ("IBS<0,1 → 1 d.", ibs < 0.1, None)]:
        pos = np.zeros(len(c)); inp = False
        for i in range(len(c)):
            if inp and (ex is None or ex.iloc[i]): inp = False
            if not inp and ent.iloc[i]: inp = True
            pos[i] = inp
        pos = pd.Series(pos, c.index)
        p1 = pos.shift(1).fillna(0)
        xa = p1 * c.pct_change().fillna(0) + (1 - p1) * cash - pos.diff().abs().fillna(0) * FEE      # MOC
        prev = p1.shift(1).fillna(0)                                                                 # kitos d. atidarymas
        xb = pd.Series(np.where((prev == 1) & (p1 == 1), c / c.shift(), np.where((prev == 0) & (p1 == 1), c / o,
              np.where((prev == 1) & (p1 == 0), o / c.shift(), 1))) - 1, c.index).fillna(0)
        xb = xb + (1 - p1) * cash * (prev == 0) - p1.diff().abs().fillna(0) * FEE
        print(f"  {nm:28s} MOC: " + " | ".join(st(xa, a, b) for a, b in PER) + f"  || atid.: " + " | ".join(st(xb, a, b) for a, b in PER) + f" | rinkoje {pos.mean()*100:.0f}%")
