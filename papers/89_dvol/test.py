"""89: Deribit DVOL (30 d. implikuotas volatilumas, „kripto VIX“) kaip signalas BTC/ETH: A) VIX logika – pirkti, kai DVOL aukštas (baimė, z > k), laikyti N d.;
B) volatilumo rizikos premija: DVOL − realizuotas 30 d. volatilumas; aukšta premija = ramu -> laikyti; C) žemas DVOL (suspaudimas) -> pramušimo laukimas su trendo kryptimi.
DVOL dienos uždarymas (00:00 UTC), 1 d. vėlavimas, Binance spot, 0,1 % mokestis. 2021-03 – 2026-11. Paleisti: quantconnect-lean/.venv/bin/python papers/89_dvol/test.py"""
import json, os, numpy as np, pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(D)
def st(e, a, b):
    e = e[(e.index >= a) & (e.index < b)]; e = e / e.iloc[0]; y = (e.index[-1] - e.index[0]).days / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+6.1f}% kr {(e / e.cummax() - 1).min() * 100:4.0f}%"
PER = [("2021-06-01", "2023-01-01"), ("2023-01-01", "2027-01-01")]
print("periodai: 2021-06–22 | 2023–26")
for c in ("BTC", "ETH"):
    dv = pd.Series({pd.to_datetime(int(k), unit="ms"): v for k, v in json.load(open(f"{D}/data/{c}.json")).items()}).sort_index()
    b = pd.read_csv(f"{R}/data/binance_1d/{c}USDT.csv"); px = pd.Series(b.c.values, pd.to_datetime(b.t, unit="ms"))
    dv = dv.reindex(px.index).ffill().shift(1)          # DVOL D 00:00 = dienos D-1 pabaiga; dar 1 d. vėlavimas saugumui
    px = px[dv.notna()]; dv = dv[dv.notna()]; r = px.pct_change().shift(-1).fillna(0)
    rv = px.pct_change().rolling(30).std() * np.sqrt(365) * 100; vrp = dv - rv
    def show(nm, pos):
        pos = pos.fillna(0); e = (1 + r * pos - pos.diff().abs().fillna(0) * 0.001).cumprod()
        print(f"{c} {nm:38s} " + " | ".join(st(e, a, b) for a, b in PER) + f" | rinkoje {pos.mean()*100:.0f}%")
    print(); show("laikyti", pd.Series(1.0, px.index))
    z = (dv - dv.rolling(90).mean()) / dv.rolling(90).std()
    for k in (1.0, 1.5, 2.0):
        for h in (10, 30):
            show(f"A DVOL z(90) > {k}, laikyti {h} d.", (z > k).astype(float).rolling(h, min_periods=1).max())
    for q in (0, 10):
        show(f"B laikyti kai VRP > {q} (DVOL − RV30)", (vrp > q).astype(float))
    show("B laikyti kai VRP < 0 (atvirkščiai)", (vrp < 0).astype(float))
    lowv = dv < dv.rolling(180).quantile(0.2); trend = px > px.rolling(50).mean()
    show("C žemas DVOL (20 %) ir kaina > SMA50", (lowv & trend).astype(float).rolling(20, min_periods=1).max())
    show("palyg.: kaina > SMA50", trend.astype(float))
