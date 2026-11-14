"""81: BTC 4 metų halvingo ciklas (populiarus: Rekt Capital, PlanB ir kt.). Fiksuotos taisyklės be derinimo: laikyti nuo X d. prieš halvingą iki Y d. po jo.
Halvingai: 2012-11-28, 2016-07-09, 2020-05-11, 2024-04-20 (kitas ~2028-04). Variantai X ∈ {500, 365, 0}, Y ∈ {365, 520, 550}.
Coin Metrics BTC nuo 2010-07, 0,1 % mokestis. Paleisti: quantconnect-lean/.venv/bin/python papers/81_halving_cycle/test.py"""
import json, os
import pandas as pd
D = os.path.dirname(os.path.abspath(__file__))
d = pd.DataFrame(json.load(open(f"{D}/data/btc.json"))["data"]); p = pd.Series(d.PriceUSD.astype(float).values, pd.to_datetime(d.time).dt.tz_localize(None))
H = pd.to_datetime(["2012-11-28", "2016-07-09", "2020-05-11", "2024-04-20", "2028-04-15"])
r = p.pct_change().shift(-1).fillna(0)
def st(e, a, b):
    e = e[(e.index >= a) & (e.index < b)]; e = e / e.iloc[0]; y = (e.index[-1] - e.index[0]).days / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+7.1f}% kr {(e / e.cummax() - 1).min() * 100:4.0f}%"
PER = [("2011-01-01", "2016-01-01"), ("2016-01-01", "2021-01-01"), ("2021-01-01", "2027-01-01")]
print("periodai: 2011–15 | 2016–20 | 2021–26")
print(f"{'laikyti':22s} " + " | ".join(st((1 + r).cumprod(), a, b) for a, b in PER))
for X in (500, 365, 0):
    for Y in (365, 520, 550):
        pos = pd.Series(0.0, p.index)
        for h in H: pos[(p.index >= h - pd.Timedelta(days=X)) & (p.index < h + pd.Timedelta(days=Y))] = 1
        e = (1 + r * pos - pos.diff().abs().fillna(0) * 0.001).cumprod()
        print(f"X={X:3d} d. prieš, Y={Y} d. po " + " | ".join(st(e, a, b) for a, b in PER) + f" | rinkoje {pos.mean()*100:.0f}%")
# jautrumas: X 400–600, Y 450–650 (2016–26) ir metai bazei (500/550)
print("\njautrumas 2016–26 %/m. (eilutės X, stulpeliai Y):")
Ys = (450, 500, 550, 600, 650); print("      " + " ".join(f"{y:>6}" for y in Ys))
for X in (400, 450, 500, 550, 600):
    row = []
    for Y in Ys:
        pos = pd.Series(0.0, p.index)
        for h in H: pos[(p.index >= h - pd.Timedelta(days=X)) & (p.index < h + pd.Timedelta(days=Y))] = 1
        e = (1 + r * pos - pos.diff().abs().fillna(0) * 0.001).cumprod(); e = e["2016":]; y = (e.index[-1] - e.index[0]).days / 365.25
        row.append(f"{((e.iloc[-1] / e.iloc[0]) ** (1 / y) - 1) * 100:+6.0f}")
    print(f"X={X} " + " ".join(row))
pos = pd.Series(0.0, p.index)
for h in H: pos[(p.index >= h - pd.Timedelta(days=500)) & (p.index < h + pd.Timedelta(days=550))] = 1
e = (1 + r * pos - pos.diff().abs().fillna(0) * 0.001).cumprod(); yr = e.resample("YE").last().pct_change().dropna(); hy = p.resample("YE").last().pct_change()
print("metai (500/550) / laikymas:", {k.year: f"{v*100:+.0f}/{hy[k]*100:+.0f}" for k, v in yr.items()})
print("įėjimai/išėjimai:", [(t.date(), int(v)) for t, v in pos[pos.diff() != 0].items()][1:])
