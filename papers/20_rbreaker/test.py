#!/usr/bin/env python3
"""#20 R-Breaker (Richard Saidenberg; populiari Kinijos ateities sandorių intraday strategija) ant BTC/ETH, 1h žvakės (Binance spot nuo 2017).
Lygiai iš vakar H/L/C: pivot, buy break, sell setup, sell enter, buy enter, buy setup, sell break.
Trendas: valandos uždarymas > buy break → long; < sell break → short. Atšokimas: dienos H > sell setup ir kaina < sell enter → short;
dienos L < buy setup ir kaina > buy enter → long. Įvykdoma kitos valandos atidarymu, uždaroma dienos gale (00 UTC).
Variantai: tik trendas / trendas+atšokimas, long / long+short. Mokestis 0,1 % (spot) ir 0,05 % (perp)."""
import numpy as np, pandas as pd


def load(s):
    d = pd.read_pickle(f"../10_sezoniskumas/data/{s}USDT.pkl").set_index("t")
    return d


def run(s, rev=True, short=True, fee=0.001):
    h1 = load(s); c = h1.c; o = h1.o
    day = c.index.floor("D")
    dly = pd.DataFrame({"h": c.groupby(day).max(), "l": c.groupby(day).min(), "c": c.groupby(day).last()})  # aproksimacija iš uždarymų
    hi = h1.c.groupby(day).cummax(); lo = h1.c.groupby(day).cummin()
    Y = dly.shift(1).reindex(day); Y.index = c.index
    H, L, C = Y.h, Y.l, Y.c; P = (H + L + C) / 3
    bb = H + 2 * (P - L); ss = P + (H - L); se = 2 * P - L; be = 2 * P - H; bs = P - (H - L); sb = L - 2 * (H - P)
    sig = pd.Series(0, c.index)
    sig[c > bb] = 1
    if short: sig[c < sb] = -1
    if rev:
        if short: sig[(hi > ss) & (c < se) & (sig == 0)] = -1
        sig[(lo < bs) & (c > be) & (sig == 0)] = 1
    # pozicija: pirmas signalas dienoje laikomas iki dienos pabaigos (paprasta versija be apsivertimų)
    pos = np.zeros(len(c)); cur = 0; last_day = None; sv = sig.values; dv = day.values
    for i in range(len(c) - 1):
        if dv[i] != last_day: cur = 0; last_day = dv[i]
        if cur == 0 and sv[i] != 0 and dv[i + 1] == dv[i]: cur = sv[i]
        pos[i + 1] = cur if dv[i + 1] == dv[i] else 0
    pos = pd.Series(pos, c.index)
    r = c.pct_change().fillna(0)
    rr = pos * r
    # įėjimas valandos atidarymu: pirmos valandos grąža o->c, mokestis įėjus ir išėjus
    entry = (pos != 0) & (pos.shift(1) == 0)
    rr[entry] = pos[entry] * (c[entry] / o[entry] - 1)
    trades = entry.sum()
    rr = rr - entry * 2 * fee
    return rr.groupby(day).apply(lambda x: (1 + x).prod() - 1), trades


def st(r, a, b):
    r = r[a:b]; eq = (1 + r).cumprod(); y = (r.index[-1] - r.index[0]).days / 365.25
    return f"{(eq.iloc[-1] ** (1 / y) - 1) * 100:+.1f} ({(eq / eq.cummax() - 1).min() * 100:.0f})"


rows = []
for name, kw in [("trendas+atšokimas, long+short", {}), ("trendas+atšokimas, long", dict(short=False)),
                 ("tik trendas, long+short", dict(rev=False)), ("tik trendas, long", dict(rev=False, short=False))]:
    for fee in [0.001, 0.0005]:
        out = [run(s, fee=fee, **kw) for s in ["BTC", "ETH"]]
        R = pd.concat([o[0] for o in out], axis=1).fillna(0).mean(axis=1)
        y = (1 + R["2021-11-08":]).groupby(R["2021-11-08":].index.year).prod() - 1
        rows.append(f"| {name} | {fee*100:.2f} | {sum(o[1] for o in out)} | {st(R, '2018-01-01', '2021-11-08')} | {st(R, '2021-11-08', '2026-11-08')} | {' '.join(f'{a}:{b*100:+.0f}' for a, b in y.items())} |")
        print(rows[-1], flush=True)
md = "| Variantas | mokestis % | sandoriai | 2018–2021-11 %/m (kritimas) | 2021-11–2026-11 | metai |\n|---|---|---|---|---|---|\n" + "\n".join(rows)
open("REZULTATAI.txt", "w").write(md + "\n")
