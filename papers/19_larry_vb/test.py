#!/usr/bin/env python3
"""#19 Larry Williams volatilumo pramušimas (Korėjos kripto botų versija): pirkti, kai kaina > atidarymas + k × (vakar H − L),
parduoti kitos dienos atidarymu (00 UTC). Variantai: k fiksuotas; k = triukšmo santykis (1 − |O−C|/(H−L), 20 d. vid.);
filtras – kaina virš 5 d. vidurkio; pozicijos dydis – 2 % / vakar diapazonas % (volatilumo taikymas, ≤ 1).
Binance spot dienos žvakės, mokestis 0,1 %, BTC+ETH ir alts10."""
import os, numpy as np, pandas as pd
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/binance_1d")
G = {"BTC+ETH": ["BTC", "ETH"], "alts10": ["XRP", "BNB", "SOL", "DOGE", "ADA", "TRX", "LINK", "AVAX", "LTC", "DOT"]}


def load(s):
    d = pd.read_csv(f"{D}/{s}USDT.csv"); d.index = pd.to_datetime(d.t, unit="ms"); return d[["o", "h", "l", "c"]]


def vb(d, k=0.5, noise=False, ma=False, size=False, fee=0.001):
    rng = (d.h - d.l).shift(1)
    if noise: k = (1 - (d.o - d.c).abs() / (d.h - d.l)).rolling(20).mean().shift(1)
    up = d.o + k * rng
    hit = d.h > up
    if ma: hit &= d.o > d.c.rolling(5).mean().shift(1)
    px = np.maximum(d.o, up)
    nxt_open = d.o.shift(-1)
    w = (0.02 / (rng / d.o)).clip(upper=1) if size else 1.0
    r = np.where(hit, (nxt_open / px - 1 - 2 * fee) * w, 0.0)
    return pd.Series(r, d.index).fillna(0)


def st(r, a, b):
    r = r[a:b]; eq = (1 + r).cumprod(); y = (r.index[-1] - r.index[0]).days / 365.25
    return f"{(eq.iloc[-1] ** (1 / y) - 1) * 100:+.1f} ({(eq / eq.cummax() - 1).min() * 100:.0f})"


V = {"k=0,5": {}, "k=0,7": dict(k=0.7), "k triukšmo": dict(noise=True), "k=0,5 + MA5": dict(ma=True),
     "triukšmo + MA5": dict(noise=True, ma=True), "triukšmo + MA5 + 2 % dydis": dict(noise=True, ma=True, size=True)}
rows = []
for g, cs in G.items():
    data = {s: load(s) for s in cs}
    h = pd.concat({s: d.c.pct_change() for s, d in data.items()}, axis=1, sort=True)["2018":].fillna(0).mean(axis=1)
    rows.append(f"| {g} | laikyti | {st(h, '2018-01-01', '2021-11-08')} | {st(h, '2021-11-08', '2026-11-08')} | |")
    for n, kw in V.items():
        R = pd.concat({s: vb(d, **kw) for s, d in data.items()}, axis=1, sort=True)["2018":].fillna(0).mean(axis=1)
        y = (1 + R["2021-11-08":]).groupby(R["2021-11-08":].index.year).prod() - 1
        rows.append(f"| {g} | {n} | {st(R, '2018-01-01', '2021-11-08')} | {st(R, '2021-11-08', '2026-11-08')} | {' '.join(f'{a}:{b*100:+.0f}' for a, b in y.items())} |")
        print(rows[-1], flush=True)
md = "| Grupė | Variantas | 2018–2021-11 %/m (kritimas) | 2021-11–2026-11 %/m (kritimas) | metai |\n|---|---|---|---|---|\n" + "\n".join(rows)
open("REZULTATAI.txt", "w").write(md + "\n")
