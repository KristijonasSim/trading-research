#!/usr/bin/env python3
"""#29 Toby Crabel „Day Trading with Short Term Price Patterns“ (1990): NR4 / NR7 / NR7+inside day.
Po siauriausios per N d. dienos kitą dieną: buy stop vakar maksimumu (short – sell stop vakar minimumu), išėjimas dienos uždarymu.
Taip pat variantas: laikyti 3 d. Dienos OHLC (įėjimas max(open, riba)). Mokestis 0,1 % (spot) ir 0,05 % (futures).
2018-01 – 2021-11 ir 2021-11 – 2026-11. BTC+ETH ir alts10."""
import os, numpy as np, pandas as pd
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/binance_1d")
G = {"BTC+ETH": ["BTC", "ETH"], "alts10": ["XRP", "BNB", "SOL", "DOGE", "ADA", "TRX", "LINK", "AVAX", "LTC", "DOT"]}
def load(s):
    d = pd.read_csv(f"{D}/{s}USDT.csv"); d.index = pd.to_datetime(d.t, unit="ms"); return d[["o", "h", "l", "c"]]
def crabel(d, n, inside, side, fee):
    rng = d.h - d.l; nr = rng <= rng.rolling(n).min()
    if inside: nr &= (d.h < d.h.shift()) & (d.l > d.l.shift())
    sig = nr.shift(1).fillna(False).astype(bool); ph = d.h.shift(1); pl = d.l.shift(1)
    r = pd.Series(0.0, d.index)
    lo = sig & (d.h > ph); px = np.maximum(d.o, ph); r[lo] += (d.c / px - 1 - 2 * fee)[lo]
    if side == "ls":  # abu stop orderiai nepriklausomi (sąlyga „long nesuveikė“ būtų ateities info)
        sh = sig & (d.l < pl); px2 = np.minimum(d.o, pl); r[sh] += (1 - d.c / px2 - 2 * fee)[sh]
    return r, int(lo.sum())
def st(R, a, b):
    R = R[a:b]; e = (1 + R).cumprod(); y = len(R) / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+.1f}%/m. DD {(e / e.cummax() - 1).min() * 100:.0f}%"
data = {s: load(s) for g in G.values() for s in g}
for g, syms in G.items():
    for n, ins in [(4, False), (7, False), (4, True), (7, True)]:
        for side in ["long", "ls"]:
            for fee in [0.001, 0.0005]:
                out = [crabel(data[s], n, ins, side, fee) for s in syms]
                R = pd.concat([o[0] for o in out], axis=1, sort=True)["2018":].fillna(0).mean(axis=1)
                y = (1 + R["2021-11-08":]).groupby(R["2021-11-08":].index.year).prod() - 1
                print(f"{g} NR{n}{'+ID' if ins else ''} {side} {fee*100:.2f}%: {st(R, '2018-01-01', '2021-11-08')} | {st(R, '2021-11-08', '2026-11-09')} | long sand. {sum(o[1] for o in out)} | " + " ".join(f"{k}:{v*100:+.0f}" for k, v in y.items()), flush=True)
