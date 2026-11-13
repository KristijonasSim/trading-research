#!/usr/bin/env python3
"""#36 Liu, Tsyvinski (2021, Review of Financial Studies) „Risks and Returns of Cryptocurrency“: laiko eilučių momentum –
praėjusios 1–4 sav. grąža prognozuoja kitą savaitę. Strategija: kas savaitę (pirmadienį 00 UTC) laikyti monetą, jei jos L sav. grąža > 0, kitaip pinigai.
BTC+ETH ir alts10 (lygūs svoriai tarp monetų su signalu, likusi dalis pinigai). 0,1 % mokestis. 2018–2021-11 ir 2021-11 – 2026-11."""
import os, numpy as np, pandas as pd
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/binance_1d")
G = {"BTC+ETH": ["BTC", "ETH"], "alts10": ["XRP", "BNB", "SOL", "DOGE", "ADA", "TRX", "LINK", "AVAX", "LTC", "DOT"]}
def load(s):
    d = pd.read_csv(f"{D}/{s}USDT.csv"); return pd.Series(d.c.values, pd.to_datetime(d.t, unit="ms"))
def st(x, a, b):
    x = x[a:b]; e = (1 + x).cumprod(); y = len(x) / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+.1f}%/m. DD {(e / e.cummax() - 1).min() * 100:.0f}%"
for g, syms in G.items():
    P = pd.DataFrame({s: load(s) for s in syms}).sort_index()["2017-10-01":]; R = P.pct_change(fill_method=None).fillna(0)
    hold = R.mean(axis=1); print(f"{g} laikyti: {st(hold, '2018-01-01', '2021-11-08')} | {st(hold, '2021-11-08', '2026-11-14')}")
    for L in [1, 2, 3, 4, 8]:
        sig = (P / P.shift(7 * L) - 1 > 0).astype(float)
        mon = P.index.dayofweek == 0
        w = sig.where(pd.Series(mon, P.index), np.nan).ffill().shift(1).fillna(0) / len(syms)   # vakar (sekm.) uždarymo signalas, laikoma visą savaitę
        w = w.where(P.notna(), 0)
        x = (w * R).sum(axis=1) - w.diff().abs().sum(axis=1).fillna(0) * 0.001
        y = (1 + x["2021-11-08":]).groupby(x["2021-11-08":].index.year).prod() - 1
        print(f"  L={L} sav.: {st(x, '2018-01-01', '2021-11-08')} | {st(x, '2021-11-08', '2026-11-14')} | " + " ".join(f"{k}:{v*100:+.0f}" for k, v in y.items()), flush=True)
