"""79: „BTC seka (pasaulinį) M2 su ~10 sav. vėlavimu“ (R. Pal, L. Alden, 2024–25). JAV M2 savaitinis (WM2NS, skelbiamas ~4 sav. vėliau) ir
JAV+euro zona+Japonija M2 doleriais (mėnesiniai, iki 2023-11). Signalas: M2 13 sav. (3 mėn.) augimas > 0 arba YoY augimas kyla (YoY > jo 13 sav. vid.),
paslinktas papildomai 0 / 10 / 12 sav. („vėlavimas“). Laikyti BTC kai signalas teigiamas, kitaip grynieji. 0,1 % mokestis.
Paleisti: ../../quantconnect-lean/.venv/bin/python test.py"""
import json, os
import pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(D)
f = lambda s: pd.read_csv(f"{D}/data/{s}.csv", index_col=0, parse_dates=True, na_values=".").iloc[:, 0].astype(float).dropna()
cm = pd.DataFrame(json.load(open(f"{R}/53_mvrv/data/cm.json"))["data"]); cm["time"] = pd.to_datetime(cm.time).dt.tz_localize(None)
btc = cm[cm.asset == "btc"].set_index("time").PriceUSD.astype(float); r = btc.pct_change().shift(-1).fillna(0)
us = f("WM2NS")
eu = f("MABMM301EZM189S") * f("DEXUSEU").resample("MS").mean(); jp = f("MABMM301JPM189S") / f("DEXJPUS").resample("MS").mean()
glob = (f("M2SL") * 1e9 + eu.reindex(f("M2SL").index) + jp.reindex(f("M2SL").index)).dropna()
glob = glob.resample("W-MON").ffill() if False else glob
def st(e, a, b):
    e = e[(e.index >= a) & (e.index < b)].dropna()
    if len(e) < 100: return "     –"
    e = e / e.iloc[0]; y = (e.index[-1] - e.index[0]).days / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+6.1f}% kr {(e / e.cummax() - 1).min() * 100:4.0f}%"
PER = [("2015-01-01", "2020-01-01"), ("2020-01-01", "2024-01-01"), ("2024-01-01", "2027-01-01")]
def show(nm, sig):
    pos = sig.reindex(btc.index, method="ffill").fillna(0)
    e = (1 + r * pos - pos.diff().abs().fillna(0) * 0.001).cumprod()
    print(f"{nm:44s} " + " | ".join(st(e, a, b) for a, b in PER) + f" | rinkoje {pos['2015':].mean()*100:.0f}%")
print("periodai: 2015–19 | 2020–23 | 2024–26 (po išpopuliarinimo)")
show("laikyti BTC", pd.Series(1.0, btc.index))
for lag in (0, 10, 12):
    s1 = (us.pct_change(13) > 0).astype(float); s1.index = s1.index + pd.Timedelta(weeks=4 + lag)
    yoy = us.pct_change(52); s2 = (yoy > yoy.rolling(13).mean()).astype(float); s2.index = s2.index + pd.Timedelta(weeks=4 + lag)
    show(f"JAV M2 13 sav. augimas > 0, +{lag} sav.", s1); show(f"JAV M2 YoY kyla, +{lag} sav.", s2)
for lag in (0, 10):
    g = glob.pct_change(3); s3 = (g > 0).astype(float); s3.index = s3.index + pd.DateOffset(months=1) + pd.Timedelta(weeks=lag)
    gy = glob.pct_change(12); s4 = (gy > gy.rolling(3).mean()).astype(float); s4.index = s4.index + pd.DateOffset(months=1) + pd.Timedelta(weeks=lag)
    show(f"JAV+EZ+JP M2 3 mėn. augimas > 0, +{lag} sav.", s3); show(f"JAV+EZ+JP M2 YoY kyla, +{lag} sav.", s4)
show("palyg.: kaina > 200 d. SMA", (btc > btc.rolling(200).mean()).astype(float))
