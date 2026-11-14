"""54 patikra: vykdymo vėlavimas (0/1/2 h), slenksčio ir laikymo zona, metai. Mokestis 0,05 % (perp)."""
import json, os
import numpy as np, pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(D)
def cagr(e):
    y = (e.index[-1] - e.index[0]).days / 365.25; return ((e.iloc[-1] / e.iloc[0]) ** (1 / y) - 1) * 100
for coin in ("BTC", "ETH"):
    cb = pd.DataFrame(json.load(open(f"{D}/data/{coin}-USD.json")), columns=["t", "l", "h", "o", "c", "v"])
    cb = pd.Series(cb.c.values, pd.to_datetime(cb.t, unit="s"))
    bn = pd.read_pickle(f"{R}/10_sezoniskumas/data/{coin}USDT.pkl"); bn = pd.Series(bn.c.values, pd.to_datetime(bn.t))
    df = pd.concat([cb.rename("cb"), bn.rename("bn")], axis=1, sort=True).dropna(); df = df[df.index >= "2019-01-01"]
    prem = df.cb / df.bn - 1; adj = prem - prem.rolling(168, min_periods=72).median()
    r = df.bn.pct_change().shift(-1).fillna(0)
    print(f"\n== {coin} ==  (2019–21 | 2022–26 | 2024-26 %/m., kritimas 2022–26)")
    for delay in (0, 1, 2):
        for k in (0.0003, 0.0005, 0.0008, 0.001):
            row = []
            for h in (12, 24, 48):
                pos = (adj > k).astype(float).rolling(h, min_periods=1).max().shift(delay).fillna(0)
                eq = (1 + r * pos - pos.diff().abs().fillna(0) * 0.0005).cumprod()
                a, b, c = eq[:"2021"], eq["2022":], eq["2024":]
                row.append(f"h{h}: {cagr(a):+5.0f} | {cagr(b):+5.1f} | {cagr(c):+5.1f} kr {(b/b.cummax()-1).min()*100:3.0f}%")
            print(f"vėl.{delay}h k={k*100:.2f}%  " + "   ".join(row))
    pos = (adj > 0.0005).astype(float).rolling(24, min_periods=1).max().shift(1).fillna(0)
    eq = (1 + r * pos - pos.diff().abs().fillna(0) * 0.0005).cumprod()
    yr = eq.resample("YE").last().pct_change(); yr.iloc[0] = eq.resample("YE").last().iloc[0] - 1
    hy = df.bn.resample("YE").last().pct_change()
    print("metai (k 0,05 %, h 24, vėl. 1h):", {k.year: f"{v*100:+.0f} (laik. {hy[k]*100:+.0f})" for k, v in yr.items()}, f"sandorių/m. ~{int((pos.diff()>0).sum()/7.9)}")
