#!/usr/bin/env python3
"""#31 BTC „CME gap'as visada užsipildo“ (populiarus Twitter/YouTube teiginys). CME BTC futures savaitgalį uždaryti:
penktadienį ~21:00 UTC (vasarą 20:00) iki sekmadienio ~22:00 (vasarą 21:00). Gap'as = sekm. kaina − penkt. kaina.
Strategija: sekmadienį atidarymo valandą, jei |gap| > X, prekiauti link penktadienio kainos (gap aukštyn -> short),
išeiti kai užsipildo (valandos uždarymu) arba po H valandų. Binance spot valandiniai o/c (BTC, ETH tikrinimui), mokestis 0,05 %/pusė.
2018-01 – 2021-11 ir 2021-11 – 2026-11."""
import os, numpy as np, pandas as pd
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../10_sezoniskumas/data")
def run(sym, X, Hmax, fee=0.0005):
    d = pd.read_pickle(f"{D}/{sym}USDT.pkl").set_index("t"); d = d[~d.index.duplicated()].c
    tr = []; fills = 0; n = 0
    for fri in d.index[(d.index.dayofweek == 4) & (d.index.hour == 20)]:   # 20:00–21:00 baro uždarymas ≈ 21:00 UTC
        sun = fri + pd.Timedelta(hours=49)     # sekmadienio 22:00 baro uždarymas
        if sun not in d.index: continue
        p0, p1 = d[fri], d[sun]; gap = p1 / p0 - 1
        if abs(gap) < X: continue
        side = -np.sign(gap); n += 1
        path = d[sun + pd.Timedelta(hours=1): sun + pd.Timedelta(hours=Hmax)]
        hit = path[(path <= p0)] if gap > 0 else path[(path >= p0)]
        ex = hit.iloc[0] if len(hit) else path.iloc[-1]; fills += len(hit) > 0
        tr.append((sun, side * (ex / p1 - 1) - 2 * fee))
    r = pd.Series(dict(tr)) if tr else pd.Series(dtype=float)
    return r, n, fills
def summ(r, a, b):
    r = r[a:b]
    if len(r) == 0: return "—"
    y = (pd.Timestamp(b) - pd.Timestamp(a)).days / 365.25
    return f"n={len(r)} vid. {r.mean()*100:+.2f}% laimi {(r>0).mean():.0%} metinė {((1+r).prod()**(1/y)-1)*100:+.1f}%"
for sym in ["BTC", "ETH"]:
    for X in [0.005, 0.01, 0.02, 0.03]:
        for Hm in [24, 72, 120]:
            r, n, f = run(sym, X, Hm)
            print(f"{sym} gap>{X*100:.1f}% max {Hm}h: užsipildė {f}/{n} | 2018–21 {summ(r, '2018-01-01', '2021-11-08')} | 2021–26 {summ(r, '2021-11-08', '2026-11-14')}", flush=True)
