#!/usr/bin/env python3
"""#51 PlanB Stock-to-Flow (2019) ir Bitcoin Rainbow (log regresijos juostos, Blockchaincenter) kaip signalai.
S2F: atsargos/metinė emisija iš blokų tvarkaraščio (10 min. blokas, halvingai 2012-11-28, 2016-07-09, 2020-05-11, 2024-04-20);
modelio kaina = exp(−1.84) × S2F^3.36 (PlanB 2019 straipsnio koeficientai). Laikyti BTC kai kaina < modelio × k.
Rainbow: log10(kaina) ~ a + b·log10(dienos nuo 2009-01-09), regresija tik iš praeities (plečiamasis langas); laikyti kai liekana < q kvantilio.
BTC, 0,1 %. 2018–2021-11 ir 2021-11 – 2026-11."""
import os, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__))
d = pd.read_csv(f"{H}/../data/binance_1d/BTCUSDT.csv"); p = pd.Series(d.c.values, pd.to_datetime(d.t, unit="ms")); r = p.pct_change().fillna(0)
genesis = pd.Timestamp("2009-01-03"); halv = [pd.Timestamp(x) for x in ["2012-11-28", "2016-07-09", "2020-05-11", "2024-04-20", "2028-04-01"]]
def supply(t):
    s, prev, rew = 0.0, genesis, 50.0
    for h in halv:
        end = min(t, h); s += max((end - prev).total_seconds(), 0) / 600 * rew
        if t <= h: return s, rew
        prev, rew = h, rew / 2
    return s, rew
s2f = pd.Series({t: (lambda S, R: S / (R * 6 * 24 * 365))(*supply(t)) for t in p.index})
model = np.exp(-1.84) * s2f ** 3.36
def st(x, a, b):
    x = x[a:b]; e = (1 + x).cumprod(); y = len(x) / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+.1f}%/m. DD {(e / e.cummax() - 1).min() * 100:.0f}%"
print(f"BTC laikyti: {st(r, '2018-01-01', '2021-11-08')} | {st(r, '2021-11-08', '2026-11-14')}")
print("kaina / S2F modelis:", {str(t.date()): round(p[t] / model[t], 2) for t in p.index[::365]})
for k in [0.5, 1.0, 2.0]:
    w = (p < model * k).astype(float).shift(1).fillna(0); x = w * r - w.diff().abs().fillna(0) * 0.001
    print(f"S2F: laikyti kai kaina < {k}× modelio: {st(x, '2018-01-01', '2021-11-08')} | {st(x, '2021-11-08', '2026-11-14')} | rinkoje {w['2021-11-08':].mean():.0%}")
# Rainbow: Binance kainos nuo 2017-08 per trumpos regresijai – naudojama plečiamasis langas nuo 2017-08 (ribotumas)
days = (p.index - pd.Timestamp("2009-01-09")).days.values; lx, ly = np.log10(days), np.log10(p.values)
res = np.full(len(p), np.nan)
for i in range(365, len(p)):
    b, a = np.polyfit(lx[:i], ly[:i], 1); res[i] = ly[i] - (a + b * lx[i])
res = pd.Series(res, p.index)
for q in [0.3, 0.5, 0.7]:
    thr = res.expanding(365).quantile(q)
    w = (res < thr).astype(float).shift(1).fillna(0); x = w * r - w.diff().abs().fillna(0) * 0.001
    print(f"Rainbow: laikyti kai liekana < {q:.0%} kvantilio: {st(x, '2018-01-01', '2021-11-08')} | {st(x, '2021-11-08', '2026-11-14')} | rinkoje {w['2021-11-08':].mean():.0%}")
