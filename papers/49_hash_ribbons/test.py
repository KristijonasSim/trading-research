#!/usr/bin/env python3
"""#49 Hash Ribbons (Charles Edwards, Capriole 2019): kapituliacija kai hashrate SMA30 < SMA60; pirkimo signalas, kai SMA30 vėl > SMA60
(originale + kainos momentum: SMA10 kainos > SMA20). Laikyti N d. (90/180/365) arba iki kitos kapituliacijos. Hashrate – blockchain.info (dienos įvertis),
naudojama su 1 d. vėlavimu. BTC, 0,1 %. 2012–2021-11 (BTC kainos – Binance tik nuo 2017-08, todėl 2017-08 – 2021-11) ir 2021-11 – 2026-11."""
import os, json, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__))
v = json.load(open(f"{H}/data/hash.json"))["values"]
hr = pd.Series({pd.to_datetime(x["x"], unit="s").normalize(): x["y"] for x in v}).sort_index()
hr = hr[~hr.index.duplicated()].resample("D").last().ffill()
d = pd.read_csv(f"{H}/../data/binance_1d/BTCUSDT.csv"); p = pd.Series(d.c.values, pd.to_datetime(d.t, unit="ms")); r = p.pct_change().fillna(0)
m30, m60 = hr.rolling(30).mean(), hr.rolling(60).mean()
cap = (m30 < m60).reindex(p.index).ffill().shift(1).fillna(False).astype(bool)
mom = p.rolling(10).mean() > p.rolling(20).mean()
recover = (~cap) & cap.shift(1).fillna(False).astype(bool)
def st(x, a, b):
    x = x[a:b]; e = (1 + x).cumprod(); y = len(x) / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+.1f}%/m. DD {(e / e.cummax() - 1).min() * 100:.0f}%"
print(f"BTC laikyti: 2017-08–21 {st(r, '2017-08-17', '2021-11-08')} | 2021–26 {st(r, '2021-11-08', '2026-11-14')}")
sig_dates = []
armed = False
buy = pd.Series(False, p.index)
for i in range(1, len(p)):
    if recover.iloc[i]: armed = True
    if cap.iloc[i]: armed = False
    if armed and mom.iloc[i]: buy.iloc[i] = True; armed = False
print("pirkimo signalai:", [str(x.date()) for x in buy[buy].index])
for hold in [90, 180, 365, "kap"]:
    w = pd.Series(0.0, p.index); left = 0
    for i in range(len(p)):
        if buy.iloc[i]: left = 10**9 if hold == "kap" else hold
        if hold == "kap" and cap.iloc[i]: left = 0
        if left > 0: w.iloc[i] = 1; left -= 1
    w = w.shift(1).fillna(0); x = w * r - w.diff().abs().fillna(0) * 0.001
    print(f"laikyti {hold} d. po signalo: 2017-08–21 {st(x, '2017-08-17', '2021-11-08')} | 2021–26 {st(x, '2021-11-08', '2026-11-14')} | rinkoje {w['2021-11-08':].mean():.0%}")
w = (~cap).astype(float).shift(1).fillna(0); x = w * r - w.diff().abs().fillna(0) * 0.001
print(f"laikyti visada, išskyrus kapituliaciją: 2017-08–21 {st(x, '2017-08-17', '2021-11-08')} | 2021–26 {st(x, '2021-11-08', '2026-11-14')}")
