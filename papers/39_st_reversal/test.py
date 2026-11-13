#!/usr/bin/env python3
"""#39 Savaitinis trumpalaikis atšokimas S&P 500 (Lehmann 1990; Jegadeesh 1990; Nagel 2012 „Evaporating liquidity“).
Kas penktadienį iš tuo metu indekse esančių akcijų pirkti 50 labiausiai per savaitę kritusių (lygūs svoriai), laikyti savaitę.
Variantas: tik kai SPY > SMA200. Palyginimas: visų narių lygiavertis krepšelis, SPY. Kaštai 0,05 % ir 0,1 % nuo apyvartos.
Duomenys ir narystės kaukė kaip #7 (papers/07_lowvol). 2001–2013 ir 2014–2026."""
import os, numpy as np, pandas as pd
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../07_lowvol"))
src = open("test.py").read().split("W = {")[0]
exec(src)
fri = pd.Series(days, days); fri = fri[fri.index.dayofweek == 4].values
r5 = C.pct_change(5, fill_method=None)
spy_ok = spy > spy.rolling(200).mean()
def run(n=50, fee=0.001, filt=False):
    W = pd.DataFrame(0.0, C.index, C.columns)
    for dt in fri[:-1]:
        if filt and not spy_ok.get(dt, True): continue
        m = [t for t in members(dt) if t in C.columns and not np.isnan(r5.at[dt, t])]
        lo = r5.loc[dt, m].nsmallest(n).index; W.loc[dt, lo] = 1 / n
    w = W.loc[fri[:-1]].reindex(C.index).ffill().fillna(0); held = w.shift(1).fillna(0)
    turn = W.loc[fri[:-1]].diff().abs().sum(axis=1).reindex(C.index).fillna(0).shift(1).fillna(0)
    return ((held * R.fillna(0)).sum(axis=1) - turn * fee)[days]
def st(r, a, b):
    r = r[a:b].dropna(); eq = (1 + r).cumprod(); y = len(r) / 252
    return f"{(eq.iloc[-1] ** (1 / y) - 1) * 100:+.1f}%/m. DD {(eq / eq.cummax() - 1).min() * 100:.0f}%"
ew = []
for dt in fri[:-1]:
    m = [t for t in members(dt) if t in C.columns and not np.isnan(C.at[dt, t])]; ew.append((dt, m))
print(f"SPY: 2001–13 {st(rs[days].fillna(0), '2001', '2014')} | 2014–26 {st(rs[days].fillna(0), '2014', '2027')}")
for n in [20, 50, 100]:
    for fee in [0.0005, 0.001]:
        for filt in [False, True]:
            x = run(n, fee, filt)
            y = (1 + x["2014":]).groupby(x["2014":].index.year).prod() - 1
            print(f"n={n} kaštai {fee*100:.2f}% {'SPY>SMA200' if filt else 'visada    '}: 2001–13 {st(x, '2001', '2014')} | 2014–26 {st(x, '2014', '2027')} | " + " ".join(f"{k}:{v*100:+.0f}" for k, v in y.items()), flush=True)
