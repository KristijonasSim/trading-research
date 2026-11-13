#!/usr/bin/env python3
"""#18 Klasikinės Jesse pavyzdžių strategijos ant kripto (dienos žvakės, Binance spot, tik long):
 - Turtle (Dennis/Faith): įėjimas 20 d. (S1) arba 55 d. (S2) maksimumo pramušimu, išėjimas 10/20 d. minimumu, stop 2N (ATR20);
 - Dual Thrust (Michael Chalek): riba = atidarymas + k × max(HH−LC, HC−LL) per 4 d., išėjimas – kitą dieną arba žemiau atid. − k×range.
Kiekviena moneta po lygią dalį (BTC+ETH: 1/2, alts10: 1/10), mokestis 0,1 %. Signalas dienos uždarymu, sandoris kitos d. kaina.
2018-01 – 2021-11 ir 2021-11 – 2026-11."""
import os, numpy as np, pandas as pd
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/binance_1d")
G = {"BTC+ETH": ["BTC", "ETH"], "alts10": ["XRP", "BNB", "SOL", "DOGE", "ADA", "TRX", "LINK", "AVAX", "LTC", "DOT"]}
FEE = 0.001


def load(s):
    d = pd.read_csv(f"{D}/{s}USDT.csv"); d.index = pd.to_datetime(d.t, unit="ms"); return d[["o", "h", "l", "c"]]


def turtle(d, ent=20, ex=10):
    hh = d.h.rolling(ent).max().shift(1); ll = d.l.rolling(ex).min().shift(1)
    tr = pd.concat([d.h - d.l, (d.h - d.c.shift()).abs(), (d.l - d.c.shift()).abs()], axis=1).max(axis=1); N = tr.rolling(20).mean()
    pos = np.zeros(len(d)); r = np.zeros(len(d)); inpos = False; stop = 0; entry = 0
    for i in range(60, len(d)):
        o, h, l, c = d.o.iloc[i], d.h.iloc[i], d.l.iloc[i], d.c.iloc[i]
        if not inpos and h > hh.iloc[i]:
            px = max(o, hh.iloc[i]); entry = px; stop = px - 2 * N.iloc[i - 1]; inpos = True
            r[i] = c / px - 1 - FEE
        elif inpos:
            ex_px = None
            if l < stop: ex_px = min(o, stop)
            elif l < ll.iloc[i]: ex_px = min(o, ll.iloc[i])
            if ex_px is not None:
                r[i] = ex_px / d.c.iloc[i - 1] - 1 - FEE; inpos = False
            else: r[i] = c / d.c.iloc[i - 1] - 1
        pos[i] = inpos
    return pd.Series(r, d.index), pos.mean()


def dual_thrust(d, n=4, k=0.5):
    rng = pd.concat([d.h.rolling(n).max() - d.c.rolling(n).min(), d.c.rolling(n).max() - d.l.rolling(n).min()], axis=1).max(axis=1).shift(1)
    up = d.o + k * rng
    hit = d.h > up
    px = np.maximum(d.o, up)
    r = np.where(hit, d.c / px - 1 - 2 * FEE, 0.0)   # įeinama dienos viduje, uždaroma uždarymu
    return pd.Series(r, d.index).fillna(0), hit.mean()


def st(r, a, b):
    r = r[a:b]; eq = (1 + r).cumprod(); y = (r.index[-1] - r.index[0]).days / 365.25
    return f"{(eq.iloc[-1] ** (1 / y) - 1) * 100:+.1f} ({(eq / eq.cummax() - 1).min() * 100:.0f})"


rows = []
for g, coins in G.items():
    data = {s: load(s) for s in coins}
    hold = pd.concat({s: d.c.pct_change() for s, d in data.items()}, axis=1)
    variants = {"laikyti": None, "Turtle S1 (20/10)": (turtle, dict(ent=20, ex=10)), "Turtle S2 (55/20)": (turtle, dict(ent=55, ex=20)),
                "Dual Thrust k=0,5": (dual_thrust, dict(k=0.5)), "Dual Thrust k=0,7": (dual_thrust, dict(k=0.7))}
    for name, v in variants.items():
        if v is None: R = hold
        else: R = pd.concat({s: v[0](d, **v[1])[0] for s, d in data.items()}, axis=1)
        port = R["2018-01-01":].fillna(0).mean(axis=1)    # kasdien perbalansuota (supaprastinta)
        rows.append(f"| {g} | {name} | {st(port, '2018-01-01', '2021-11-08')} | {st(port, '2021-11-08', '2026-11-08')} |")
        print(rows[-1], flush=True)
md = "| Grupė | Strategija | 2018–2021-11 %/m (kritimas) | 2021-11–2026-11 %/m (kritimas) |\n|---|---|---|---|\n" + "\n".join(rows)
open("REZULTATAI.txt", "w").write(md + "\n")
