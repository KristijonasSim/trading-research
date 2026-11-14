"""65: Tinklo augimas (Liu, Tsyvinski 2021 „Risks and Returns of Cryptocurrency“, RFS): aktyvių adresų augimas prognozuoja grąžą.
A) laiko eilutė BTC/ETH: laikyti, kai aktyvių adresų 30 d. vidurkis > 90 d. vidurkio (arba 4 sav. augimas > 0).
B) skerspjūvis 15 senų monetų (įsk. nuosmukio – DASH, ZEC, XMR, ETC): kas savaitę long 1/3 su didžiausiu 4 sav. adresų augimu.
Coin Metrics, 1 d. vėlavimas, 0,1 % mokestis. Paleisti: quantconnect-lean/.venv/bin/python papers/65_network_growth/test.py"""
import json, os
import numpy as np, pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); FEE = 0.001
d = pd.DataFrame(json.load(open(f"{D}/data/adr.json"))); d["time"] = pd.to_datetime(d.time).dt.tz_localize(None)
A = d.pivot(index="time", columns="asset", values="AdrActCnt").astype(float); P = d.pivot(index="time", columns="asset", values="PriceUSD").astype(float)
def st(e, a, b):
    e = e[(e.index >= a) & (e.index < b)].dropna(); e = e / e.iloc[0]; y = (e.index[-1] - e.index[0]).days / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+6.1f}% kr {(e / e.cummax() - 1).min() * 100:4.0f}%"
PER = [("2017-01-01", "2020-01-01"), ("2020-01-01", "2023-01-01"), ("2023-01-01", "2027-01-01")]
print("periodai: 2017–19 | 2020–22 | 2023–26 (straipsnio duomenys iki 2018)")
for c in ("btc", "eth"):
    p = P[c].dropna(); a = A[c].reindex(p.index); r = p.pct_change().shift(-1).fillna(0)
    def show(nm, pos):
        pos = pos.fillna(0); e = (1 + r * pos - pos.diff().abs().fillna(0) * FEE).cumprod()
        print(f"{c.upper()} {nm:34s} " + " | ".join(st(e, x, y) for x, y in PER) + f" | rinkoje {pos.mean()*100:3.0f}%")
    print(); show("laikyti", pd.Series(1.0, p.index))
    for s, l in ((7, 30), (30, 90), (30, 180)):
        show(f"adresų {s} d. vid. > {l} d. vid.", (a.rolling(s).mean() > a.rolling(l).mean()).astype(float))
    show("adresų 4 sav. augimas > 0", (a.rolling(7).mean().pct_change(28) > 0).astype(float))
    show("palyg.: kaina > 100 d. SMA", (p > p.rolling(100).mean()).astype(float))
print("\nB skerspjūvis (15 monetų, kas 7 d.)")
R1 = P.pct_change(fill_method=None)
for lb in (7, 28):
    S = np.log(A.rolling(7).mean()).diff(lb)
    for lab, sgn in (("didžiausias augimas", 1), ("mažiausias augimas", -1), ("visos lygiai", 0)):
        eq, dates, wprev = [1.0], [P.index[0]], pd.Series(0.0, P.columns)
        for i in range(200, len(P) - 1, 7):
            ok = S.iloc[i].dropna().index.intersection(P.iloc[i].dropna().index)
            if len(ok) < 8: continue
            k = max(1, len(ok) // 3); w = pd.Series(0.0, P.columns)
            if sgn == 0: w[ok] = 1 / len(ok)
            else: w[(sgn * S.iloc[i][ok]).nlargest(k).index] = 1 / k
            cost = (w - wprev).abs().sum() * FEE; j = min(i + 7, len(P) - 1)
            rr = R1.iloc[i + 1:j + 1][w[w > 0].index].fillna(0); val = ((1 + rr).cumprod() * w[w > 0]).sum(axis=1)
            e0 = eq[-1] * (1 - cost); eq += list(e0 * val.values); dates += list(rr.index); wprev = w
        e = pd.Series(eq, dates); print(f" {lb:2d} d. {lab:22s} " + " | ".join(st(e, x, y) for x, y in PER))
