"""64: Mėnulio fazių efektas (Dichev, Janes 2003; Yuan, Zheng, Zhu 2006): grąžos aplink jaunatį didesnės nei aplink pilnatį.
Taisyklė: laikyti 15 d. aplink jaunatį (±7 d.), kitu metu grynieji. Fazė apskaičiuojama astronomiškai (sinodinis mėnuo 29,530588 d. nuo 2000-01-06 18:14 UTC jaunaties).
SPY (Yahoo, 2001–26) ir BTC (Coin Metrics, 2014–26), kaštai 0,03 % / 0,1 %. Paleisti: quantconnect-lean/.venv/bin/python papers/64_lunar/test.py"""
import os, json, numpy as np, pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(D)
spy = pd.read_csv(f"{R}/59_ibs/data/SPY.csv", index_col=0, parse_dates=True).Close
cm = pd.DataFrame(json.load(open(f"{R}/53_mvrv/data/cm.json"))["data"]); cm["time"] = pd.to_datetime(cm.time).dt.tz_localize(None)
btc = cm[cm.asset == "btc"].set_index("time").PriceUSD.astype(float)
ref = pd.Timestamp("2000-01-06 18:14")
def age(idx): return ((idx - ref).total_seconds() / 86400) % 29.530588     # 0 = jaunatis, ~14,8 = pilnatis
def st(x, a, b):
    x = x[a:b].dropna(); e = (1 + x).cumprod(); y = (x.index[-1] - x.index[0]).days / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+5.1f}% kr {(e / e.cummax() - 1).min() * 100:3.0f}%"
for nm, px, fee, PER in (("SPY", spy, 0.0003, [("2001", "2012"), ("2013", "2026")]), ("BTC", btc, 0.001, [("2014", "2019"), ("2020", "2026")])):
    r = px.pct_change().fillna(0); a = pd.Series(age(px.index), px.index)
    near_new = ((a < 7.4) | (a > 22.1)).astype(float)       # ±7,4 d. aplink jaunatį
    print(f"\n{nm} laikyti: " + " | ".join(st(r, x, y) for x, y in PER))
    for lab, pos in (("jaunaties pusė", near_new), ("pilnaties pusė", 1 - near_new)):
        p1 = pos.shift(1).fillna(0); xr = p1 * r - pos.diff().abs().fillna(0) * fee
        print(f"  {lab:15s} " + " | ".join(st(xr, x, y) for x, y in PER) + f" | vid. d. grąža {r[p1 == 1].mean()*1e4:+.1f} bp")
    t = r.groupby(near_new.shift(1)).agg(["mean", "std", "count"]); diff = t["mean"].iloc[1] - t["mean"].iloc[0]
    se = np.sqrt((t["std"] ** 2 / t["count"]).sum()); print(f"  skirtumas jaunatis − pilnatis {diff*1e4:+.1f} bp/d., t = {diff/se:+.2f}")
