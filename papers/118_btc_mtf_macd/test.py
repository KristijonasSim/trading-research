"""118: BTC kelių laikotarpių MACD trendas (Quantpedia 2025 idėja). Long kai dienos MACD(12,26,9) > signalo,
variantai: + savaitės MACD > signalo filtras, + savaitės MACD > 0. Signalas dienos uždaryme, pozicija nuo kitos dienos.
Mokestis 0,1 % ratui. Taip pat ETH. 2018–2021-11 ir 2021-11–2026-11."""
import os, pandas as pd, numpy as np
D = os.path.expanduser("~/Desktop/trading-research/papers/data/binance_1d")
FEE = 0.001
def macd(c, f=12, s=26, g=9):
    m = c.ewm(span=f, adjust=False).mean() - c.ewm(span=s, adjust=False).mean(); return m, m.ewm(span=g, adjust=False).mean()
def st(r, a, z):
    r = r[(r.index >= a) & (r.index < z)]; e = (1 + r).cumprod(); y = (r.index[-1] - r.index[0]).days / 365.25
    yr = r.groupby(r.index.year).apply(lambda x: (1 + x).prod() - 1).mul(100).round(0).astype(int).to_dict()
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+.1f} | {(e / e.cummax() - 1).min() * 100:.0f} % | {yr}"
out = ["# 118 BTC/ETH kelių laikotarpių MACD – rezultatai\n", "| Moneta | Variantas | 2018–21 %/m. | kritimas | metai | 2021–26 %/m. | kritimas | metai |", "|---|---|---|---|---|---|---|---|"]
for c in ["BTC", "ETH"]:
    d = pd.read_csv(f"{D}/{c}USDT.csv"); px = pd.Series(d.c.values, pd.to_datetime(d.t, unit="ms")); r = px.pct_change().fillna(0)
    m, s = macd(px)
    w = px.resample("W-SUN").last(); wm, ws = macd(w)
    # savaitės reikšmė žinoma tik sekmadienio uždaryme -> naudoti nuo pirmadienio
    wup = (wm > ws).reindex(px.index, method="ffill").shift(1).fillna(False).astype(bool)
    wpos = (wm > 0).reindex(px.index, method="ffill").shift(1).fillna(False).astype(bool)
    sma = px.rolling(200).mean()
    V = {"laikyti": pd.Series(True, px.index), "dienos MACD": m > s, "dienos + savaitės MACD": (m > s) & wup,
         "dienos MACD + savaitės MACD > 0": (m > s) & wpos, "savaitės MACD": wup, "dienos MACD + SMA200": (m > s) & (px > sma)}
    for n, sig in V.items():
        pos = sig.astype(int).shift(1).fillna(0); ret = pos * r - pos.diff().abs().fillna(0) * FEE / 2
        out.append(f"| {c} | {n} | {st(ret, '2018-01-01', '2021-11-08')} | {st(ret, '2021-11-08', '2026-11-08')} |")
open("rezultatai_raw.md", "w").write("\n".join(out) + "\n"); print("\n".join(out))
