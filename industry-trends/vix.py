"""Volatilumo rizikos premija: SVXY (short VIX ateities sandoriai) tik kai VIX kreivė rami.
V1: SVXY, kai VIX/VIX3M < riba, kitaip grynieji.
V2 (dvigubas signalas, kaip QuantConnect tyrime 21143): kai VIX > SPY 20 d. realizuotas svyravimas IR VIX < VIX3M ->
    x dalis SVXY + likusi SPY; kitaip 100 % SPY.
Signalas uždarymu, pozicija nuo kitos dienos; 0,1 % už perjungimą; grynieji = T-bill.
"""
import sys
import numpy as np
import pandas as pd

d = pd.read_pickle(sys.argv[1])["Close"]
d = d[d.SVXY.notna()].ffill()
r = d[["SVXY", "SPY", "QQQ"]].pct_change().fillna(0)
cash = (d["^IRX"] / 100 / 252).fillna(0)
ratio = d["^VIX"] / d["^VIX3M"]
rv = r.SPY.rolling(20).std() * np.sqrt(252) * 100
vrp = d["^VIX"] > rv


def strat(w_svxy):  # w_svxy: svoris, nuspręstas dienos uždarymu (likutis – grynieji arba SPY)
    return w_svxy


def run(w_sv, w_spy):
    ws, wp = w_sv.shift(1).fillna(0), w_spy.shift(1).fillna(0)
    turn = (w_sv.diff().abs() + w_spy.diff().abs()).shift(1).fillna(0)
    return ws * r.SVXY + wp * r.SPY + (1 - ws - wp).clip(lower=0) * cash - turn * 0.001


def st(x, a, b):
    x = x[a:b]; eq = (1 + x).cumprod(); y = len(x) / 252
    return f"{100*(eq.iloc[-1]**(1/y)-1):6.1f}%/m krit.{100*(1-eq/eq.cummax()).max():3.0f}%"


P = [("2011-10-05", "2017-12-31"), ("2018-01-01", "2018-12-31"), ("2019-01-01", "2026-11-10"), ("2021-01-01", "2026-11-10"), ("2011-10-05", "2026-11-10")]
print(" " * 34 + " | ".join(f"{a[:4]}-{b[:4]}".ljust(20) for a, b in P))
rows = [("laikyti SPY", r.SPY), ("laikyti QQQ", r.QQQ), ("laikyti SVXY", r.SVXY)]
z = pd.Series(0.0, d.index)
for th in (1.0, 0.95, 0.9):
    rows.append((f"V1 SVXY kai VIX/VIX3M<{th}", run((ratio < th).astype(float), z)))
for x in (0.3, 0.5, 1.0):
    sig = (vrp & (ratio < 1)).astype(float)
    rows.append((f"V2 {int(x*100)}% SVXY + SPY", run(sig * x, 1 - sig * x)))
for lab, s in rows:
    print(f"{lab:34}" + " | ".join(st(s, a, b).ljust(20) for a, b in P))
s = run((vrp & (ratio < 1)).astype(float) * 0.3, 1 - (vrp & (ratio < 1)).astype(float) * 0.3)
print("V2 30% pagal metus:", s.groupby(s.index.year).apply(lambda x: round(100 * ((1 + x).prod() - 1))).to_dict())
print("SPY pagal metus:   ", r.SPY.groupby(r.index.year).apply(lambda x: round(100 * ((1 + x).prod() - 1))).to_dict())
