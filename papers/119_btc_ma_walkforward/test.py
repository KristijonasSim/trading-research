"""119: Mroziewicz, Ślepaczuk 2026 idėja. Long-only (ir long/short variantas) kai greitas SMA > lėtas SMA, 1h ir 4h.
Walk-forward: kas 3 mėn. parenkami (greitas, lėtas) pagal geriausią Calmar praeitų 12 mėn., taikomi kitus 3 mėn.
BTC parametrai perkeliami į ETH/BNB (kaip straipsnyje). Mokestis 0,1 % ratui. Rezultatai 2018-07 – 2021-11 ir 2021-11 – 2026-11."""
import os, itertools, numpy as np, pandas as pd
D = os.path.expanduser("~/Desktop/trading-research/freqtrade/user_data/data/binance")
FEE = 0.001
FAST = [5, 10, 20, 30, 50]; SLOW = [50, 100, 150, 200, 300, 400]
def load(c, tf):
    d = pd.read_feather(f"{D}/{c}_USDT-1h.feather").set_index("date").close; d.index = d.index.tz_localize(None)
    return d.resample(tf).last().dropna() if tf != "1h" else d
def rets(px, f, s, short):
    sig = (px.rolling(f).mean() > px.rolling(s).mean()).astype(int)
    if short: sig = sig * 2 - 1
    pos = sig.shift(1).fillna(0); return pos * px.pct_change().fillna(0) - pos.diff().abs().fillna(0) * FEE / 2
def calmar(r):
    e = (1 + r).cumprod(); dd = -(e / e.cummax() - 1).min(); return (e.iloc[-1] - 1) / max(dd, 0.05)
def wf(px_by, short, tf):
    allr = {c: {(f, s): rets(px, f, s, short) for f, s in itertools.product(FAST, SLOW) if f < s} for c, px in px_by.items()}
    idx = px_by["BTC"].index; starts = pd.date_range("2018-07-01", "2026-11-01", freq="3MS"); out = {c: [] for c in px_by}; chosen = []
    for a, b in zip(starts[:-1], starts[1:]):
        tr = {k: v[(v.index >= a - pd.DateOffset(months=12)) & (v.index < a)] for k, v in allr["BTC"].items()}
        best = max(tr, key=lambda k: calmar(tr[k])); chosen.append(best)
        for c in px_by: r = allr[c][best]; out[c].append(r[(r.index >= a) & (r.index < b)])
    return {c: pd.concat(v) for c, v in out.items()}, chosen
def st(r, a, z):
    r = r[(r.index >= a) & (r.index < z)]; e = (1 + r).cumprod(); y = (r.index[-1] - r.index[0]).days / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+.1f} | {(e / e.cummax() - 1).min() * 100:.0f} %"
out = ["# 119 MA walk-forward – rezultatai\n", "| Laikotarpis | Variantas | Moneta | 2018-07–2021-11 %/m. | kritimas | 2021-11–2026-11 %/m. | kritimas |", "|---|---|---|---|---|---|---|"]
for tf in ["1h", "4h"]:
    px = {c: load(c, tf) for c in ["BTC", "ETH", "BNB"]}
    for c in px: out.append(f"| {tf} | laikyti | {c} | {st(px[c].pct_change().fillna(0), '2018-07-01', '2021-11-08')} | {st(px[c].pct_change().fillna(0), '2021-11-08', '2026-11-08')} |")
    for short in [False, True]:
        R, ch = wf(px, short, tf)
        for c in R: out.append(f"| {tf} | WF {'long/short' if short else 'long'} | {c} | {st(R[c], '2018-07-01', '2021-11-08')} | {st(R[c], '2021-11-08', '2026-11-08')} |")
        print(tf, short, ch[-6:], flush=True)
open("rezultatai_raw.md", "w").write("\n".join(out) + "\n"); print("\n".join(out))
