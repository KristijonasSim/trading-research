"""56: Kimchi premija (Upbit KRW kaina / (Binance USDT kaina × USD/KRW) − 1). Teiginys: aukšta premija = Korėjos euforija = viršūnė.
Dienos uždarymai (UTC), USD/KRW – ECB (frankfurter.app), 1 d. vėlavimas, mokestis 0,1 %. Prekyba Binance spot.
Paleisti: ../../quantconnect-lean/.venv/bin/python test.py"""
import json, os
import pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(D); FEE = 0.001
fx = pd.Series({k: v["KRW"] for k, v in json.load(open(f"{D}/data/usdkrw.json"))["rates"].items()}); fx.index = pd.to_datetime(fx.index)
def st(e, a, b):
    e = e[(e.index >= a) & (e.index < b)]; e = e / e.iloc[0]; y = (e.index[-1] - e.index[0]).days / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+6.1f}%/m. kr {(e / e.cummax() - 1).min() * 100:4.0f}%"
P = [("2018-01-01", "2022-01-01"), ("2022-01-01", "2027-01-01"), ("2024-01-01", "2027-01-01")]
print("periodai: 2018–21 | 2022–26 | 2024–26")
for c in ("BTC", "ETH", "XRP"):
    up = pd.Series(json.load(open(f"{D}/data/KRW-{c}.json"))); up.index = pd.to_datetime(up.index)
    b = pd.read_csv(f"{R}/data/binance_1d/{c}USDT.csv"); bn = pd.Series(b.c.values, pd.to_datetime(b.t, unit="ms"))
    df = pd.concat([up.rename("up"), bn.rename("bn"), fx.rename("fx")], axis=1, sort=True); df["fx"] = df.fx.ffill()
    df = df.dropna(); df = df[df.index >= "2017-10-01"]
    prem = df.up / (df.bn * df.fx) - 1
    r = df.bn.pct_change().shift(-1).fillna(0)
    def show(nm, pos):
        pos = pos.shift(1).fillna(0)   # 1 d. vėlavimas
        e = (1 + r * pos - pos.diff().abs().fillna(0) * FEE).cumprod()
        print(f"{nm:38s} " + " | ".join(st(e, a, bb) for a, bb in P) + f" | rinkoje {pos.mean()*100:3.0f}%, sandorių {int((pos.diff().abs()>0).sum())}")
    print(f"\n== {c} ==  premija: mediana {prem.median()*100:.1f} %, max {prem.max()*100:.0f} %, 2024–26 mediana {prem['2024':].median()*100:.1f} %")
    show("laikyti", pd.Series(1.0, prem.index))
    for x in (0.03, 0.05, 0.08, 0.10):
        show(f"A laikyti kai premija < {x*100:.0f}%", (prem < x).astype(float))
    for n in (30, 90):
        d = prem - prem.rolling(n).median()
        for k in (0.01, 0.02, 0.04):
            show(f"B grynieji kai premija > {n}d med. + {k*100:.0f}%", (d < k).astype(float))
    for n in (7, 30):
        show(f"C laikyti kai premija > {n}d vid. (trendas)", (prem > prem.rolling(n).mean()).astype(float))
