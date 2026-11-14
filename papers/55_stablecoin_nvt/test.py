"""55: A) stablecoin'ų emisija (USDT+USDC pasiūlos augimas -> BTC/ETH kyla; populiarus on-chain teiginys);
B) Willy Woo NVT Signal (2018): rinkos kapitalizacija / 90 d. vid. on-chain apyvarta; aukštas = perkaista.
Duomenys: Coin Metrics community (SplyCur, PriceUSD, CapMrktCurUSD), blockchain.info estimated-transaction-volume-usd.
Signalas dienos t pabaigoje, prekyba t+1 (1 d. vėlavimas), mokestis 0,1 %. Paleisti: python3 test.py (iš šio aplanko, pandas)."""
import json, os
import numpy as np, pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); FEE = 0.001
def cm(f, col):
    d = pd.DataFrame(json.load(open(f"{D}/data/{f}"))["data"]); d["time"] = pd.to_datetime(d.time).dt.tz_localize(None)
    return d.pivot(index="time", columns="asset", values=col).astype(float)
px = cm("px.json", "PriceUSD"); mc = cm("px.json", "CapMrktCurUSD")
sup = cm("stable.json", "SplyCur").fillna(0).sum(axis=1)
tv = pd.DataFrame(json.load(open(f"{D}/data/txvol.json"))["values"]); tv = pd.Series(tv.y.values, pd.to_datetime(tv.x, unit="s")).resample("1D").last().ffill()
def bt(p, pos):
    pos = pos.reindex(p.index).ffill().fillna(0).shift(1).fillna(0)
    return (1 + p.pct_change().fillna(0) * pos - pos.diff().abs().fillna(0) * FEE).cumprod()
def st(e, a, b):
    e = e[(e.index >= a) & (e.index < b)]; e = e / e.iloc[0]; y = (e.index[-1] - e.index[0]).days / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+6.1f}%/m. kr {(e / e.cummax() - 1).min() * 100:4.0f}%"
P = [("2019-01-01", "2022-01-01"), ("2022-01-01", "2027-01-01"), ("2024-01-01", "2027-01-01")]
def show(nm, e, pos=None):
    n = f" | sandorių {int((pos.diff().abs() > 0).sum())}, rinkoje {pos['2019':].mean()*100:.0f}%" if pos is not None else ""
    print(f"{nm:42s} " + " | ".join(st(e, a, b) for a, b in P) + n)
print("periodai: 2019–21 | 2022–26 | 2024–26")
for a in ("btc", "eth"):
    p = px[a].dropna(); print(f"\n== {a.upper()} =="); show("laikyti", p / p.iloc[0])
    for n in (7, 14, 30, 60):
        g = sup.pct_change(n)
        for thr in (0.0, 0.01):
            pos = (g > thr).astype(float); show(f"A stable augimas {n} d. > {thr*100:.0f}%", bt(p, pos), pos)
    pos = (px[a] > px[a].rolling(100).mean()).astype(float); show("palyginimui: kaina > 100 d. SMA", bt(p, pos), pos)
# NVT tik BTC
p = px["btc"].dropna(); nvts = (mc["btc"] / tv.rolling(90).mean()).dropna()
print("\n== BTC NVT Signal ==")
for win in (365, 730):
    z = (nvts - nvts.rolling(win).mean()) / nvts.rolling(win).std()
    for thr in (0.0, 1.0, 2.0):
        pos = (z < thr).astype(float); show(f"B NVTS z({win}) < {thr}", bt(p, pos), pos)
for n in (30, 90):
    pos = (nvts < nvts.rolling(n).mean()).astype(float); show(f"B NVTS < jo {n} d. vid.", bt(p, pos), pos)
    pos = (nvts > nvts.rolling(n).mean()).astype(float); show(f"B NVTS > jo {n} d. vid. (atvirkščiai)", bt(p, pos), pos)
