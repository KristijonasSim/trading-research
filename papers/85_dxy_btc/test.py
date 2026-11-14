"""85: Dolerio indekso trendas -> BTC (populiarus teiginys: silpnas doleris = kylantis BTC). FRED DTWEXBGS (platus dolerio indeksas, kasdien, skelbiamas su ~1 d. vėlavimu).
Taisyklės: laikyti BTC/ETH (arba QQQ), kai dolerio indeksas < N d. vidurkis (N = 50/100/200) arba 20 d. pokytis < 0. 2 d. vėlavimas, mokestis 0,1 % (kripto), 0,03 % (QQQ).
Paleisti: quantconnect-lean/.venv/bin/python papers/85_dxy_btc/test.py"""
import json, os
import pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(D)
dx = pd.read_csv(f"{D}/DTWEXBGS.csv", index_col=0, parse_dates=True, na_values=".").iloc[:, 0].dropna()
cm = pd.DataFrame(json.load(open(f"{R}/53_mvrv/data/cm.json"))["data"]); cm["time"] = pd.to_datetime(cm.time).dt.tz_localize(None)
qqq = pd.read_csv(f"{R}/59_ibs/data/QQQ.csv", index_col=0, parse_dates=True).Close
def st(e, a, b):
    e = e[(e.index >= a) & (e.index < b)]; e = e / e.iloc[0]; y = (e.index[-1] - e.index[0]).days / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+6.1f}% kr {(e / e.cummax() - 1).min() * 100:4.0f}%"
PER = [("2015-01-01", "2020-01-01"), ("2020-01-01", "2023-01-01"), ("2023-01-01", "2027-01-01")]
print("periodai: 2015–19 | 2020–22 | 2023–26")
for nm, px, fee in (("BTC", cm[cm.asset == "btc"].set_index("time").PriceUSD.astype(float), 0.001), ("ETH", cm[cm.asset == "eth"].set_index("time").PriceUSD.astype(float).dropna(), 0.001), ("QQQ", qqq, 0.0003)):
    r = px.pct_change().shift(-1).fillna(0); d = dx.reindex(px.index, method="ffill").shift(2)
    def show(lab, pos):
        pos = pos.fillna(0); e = (1 + r * pos - pos.diff().abs().fillna(0) * fee).cumprod()
        print(f"{nm} {lab:30s} " + " | ".join(st(e, a, b) for a, b in PER) + f" | rinkoje {pos.mean()*100:.0f}%")
    print(); show("laikyti", pd.Series(1.0, px.index))
    for n in (50, 100, 200): show(f"doleris < {n} d. vidurkis", (d < d.rolling(n).mean()).astype(float))
    show("dolerio 20 d. pokytis < 0", (d.pct_change(20) < 0).astype(float))
    show("palyg.: kaina > 200 d. SMA", (px > px.rolling(200).mean()).astype(float))
