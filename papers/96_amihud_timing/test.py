"""96: Nelikvidumo rinkos laikas (Amihud 2002; kripto – Brauneis ir kt. 2021, Leirvik 2022): Amihud ILLIQ = |r| / apyvarta (USDT), 30 d. vidurkis.
Taisyklės: laikyti BTC/ETH, kai ILLIQ < jo 365 d. mediana (likvidi rinka) arba kai ILLIQ krenta (30 d. vid. < 90 d. vid.). Binance spot 1d, 1 d. vėlavimas, 0,1 %.
Paleisti: quantconnect-lean/.venv/bin/python papers/96_amihud_timing/test.py"""
import os, pandas as pd
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def st(e, a, b):
    e = e[(e.index >= a) & (e.index < b)]; e = e / e.iloc[0]; y = (e.index[-1] - e.index[0]).days / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+6.1f}% kr {(e / e.cummax() - 1).min() * 100:4.0f}%"
PER = [("2019-01-01", "2022-01-01"), ("2022-01-01", "2027-01-01")]
print("periodai: 2019–21 | 2022–26")
for c in ("BTC", "ETH"):
    b = pd.read_csv(f"{R}/data/binance_1d/{c}USDT.csv"); px = pd.Series(b.c.values, pd.to_datetime(b.t, unit="ms")); qv = pd.Series(b.qv.values, px.index)
    r = px.pct_change(); il = (r.abs() / qv * 1e9).rolling(30).mean(); fr = r.shift(-1).fillna(0)
    def show(nm, pos):
        pos = pos.fillna(0); e = (1 + fr * pos - pos.diff().abs().fillna(0) * 0.001).cumprod()
        print(f"{c} {nm:36s} " + " | ".join(st(e, a, b) for a, b in PER) + f" | rinkoje {pos.mean()*100:.0f}%")
    print(); show("laikyti", pd.Series(1.0, px.index))
    show("ILLIQ < 365 d. mediana", (il < il.rolling(365).median()).astype(float))
    show("ILLIQ > 365 d. mediana (atvirkščiai)", (il > il.rolling(365).median()).astype(float))
    show("ILLIQ 30 d. < 90 d. vid. (krenta)", (il < il.rolling(90).mean()).astype(float))
    show("palyg.: kaina > 200 d. SMA", (px > px.rolling(200).mean()).astype(float))
