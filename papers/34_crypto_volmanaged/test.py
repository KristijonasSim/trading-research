#!/usr/bin/env python3
"""#34 Volatilumu valdomas kripto laikymas (Moreira, Muir 2017 metodas; kripto – Kim & Kim / „Volatility-managed crypto“ tyrimai).
Svoris = tikslinis vol / realizuotas N d. vol (riba 0–1x, be sverto), perbalansavimas kas savaitę; variantas + trendo filtras (close > SMA100).
BTC, ETH ir BTC+ETH. Mokestis 0,1 % nuo apyvartos. 2018–2021-11 ir 2021-11 – 2026-11."""
import os, numpy as np, pandas as pd
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/binance_1d")
def load(s):
    d = pd.read_csv(f"{D}/{s}USDT.csv"); return pd.Series(d.c.values, pd.to_datetime(d.t, unit="ms"))
P = pd.DataFrame({s: load(s) for s in ["BTC", "ETH"]}).dropna(); R = P.pct_change().fillna(0)
def st(x, a, b):
    x = x[a:b]; e = (1 + x).cumprod(); y = len(x) / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+.1f}%/m. DD {(e / e.cummax() - 1).min() * 100:.0f}%"
for grp in [["BTC"], ["ETH"], ["BTC", "ETH"]]:
    hold = R[grp].mean(axis=1)
    print(f"{'+'.join(grp)} laikyti: {st(hold, '2018-01-01', '2021-11-08')} | {st(hold, '2021-11-08', '2026-11-14')}")
    for tv in [0.3, 0.5]:
        for N in [20, 60]:
            for trend in [False, True]:
                out = []
                for s in grp:
                    vol = R[s].rolling(N).std() * np.sqrt(365)
                    w = (tv / vol).clip(upper=1.0)
                    if trend: w = w * (P[s] > P[s].rolling(100).mean())
                    w = w.where(np.arange(len(w)) % 7 == 0).ffill().shift(1).fillna(0)
                    out.append(w * R[s] - w.diff().abs().fillna(0) * 0.001)
                x = pd.concat(out, axis=1).mean(axis=1)
                y = (1 + x["2021-11-08":]).groupby(x["2021-11-08":].index.year).prod() - 1
                print(f"  tikslas {tv:.0%} N={N} {'+trendas' if trend else '        '}: {st(x, '2018-01-01', '2021-11-08')} | {st(x, '2021-11-08', '2026-11-14')} | " + " ".join(f"{k}:{v*100:+.0f}" for k, v in y.items()), flush=True)
