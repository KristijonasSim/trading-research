#!/usr/bin/env python3
"""#48 Crypto Fear & Greed indeksas (alternative.me, nuo 2018-02) kaip kontrarinis signalas („būk godus, kai kiti bijo“ – populiari strategija).
A) pirkti BTC kai FGI < X, parduoti kai FGI > Y; B) trendo variantas – laikyti kai FGI > 50. FGI dienos D reikšmė skelbiama 00:00 UTC (apie praėjusią dieną),
naudojama pozicijai nuo D+1 (konservatyviai). BTC ir ETH, 0,1 %. 2018-02 – 2021-11 ir 2021-11 – 2026-11."""
import os, json, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__))
f = json.load(open(f"{H}/data/fng.json"))["data"]
fg = pd.Series({pd.to_datetime(int(x["timestamp"]), unit="s"): int(x["value"]) for x in f}).sort_index()
def load(s):
    d = pd.read_csv(f"{H}/../data/binance_1d/{s}USDT.csv"); return pd.Series(d.c.values, pd.to_datetime(d.t, unit="ms"))
def st(x, a, b):
    x = x[a:b]; e = (1 + x).cumprod(); y = len(x) / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+.1f}%/m. DD {(e / e.cummax() - 1).min() * 100:.0f}%"
for s in ["BTC", "ETH"]:
    p = load(s)["2018-02-01":]; r = p.pct_change().fillna(0); g = fg.reindex(p.index).ffill()
    print(f"{s} laikyti: {st(r, '2018-02-01', '2021-11-08')} | {st(r, '2021-11-08', '2026-11-14')}")
    for X, Y in [(10, 50), (20, 60), (25, 75), (20, 80), (30, 70), (40, 90)]:
        pos = np.zeros(len(p)); inp = False
        for i in range(len(p)):
            if not inp and g.iloc[i] < X: inp = True
            elif inp and g.iloc[i] > Y: inp = False
            pos[i] = inp
        w = pd.Series(pos, p.index).shift(1).fillna(0)
        x = w * r - w.diff().abs().fillna(0) * 0.001
        print(f"  pirkti <{X}, parduoti >{Y}: {st(x, '2018-02-01', '2021-11-08')} | {st(x, '2021-11-08', '2026-11-14')} | rinkoje {w['2021-11-08':].mean():.0%}", flush=True)
    for th in [50, 60]:
        w = (g > th).astype(float).shift(1).fillna(0); x = w * r - w.diff().abs().fillna(0) * 0.001
        print(f"  trendas FGI > {th}: {st(x, '2018-02-01', '2021-11-08')} | {st(x, '2021-11-08', '2026-11-14')}")
