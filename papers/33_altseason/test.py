#!/usr/bin/env python3
"""#33 BTC ↔ altcoin'ų rotacija („Altcoin Season Index“, blockchaincenter.net; dvigubas momentum Antonacci kripto variantas).
Kas savaitę: jei altcoin'ų krepšelio (top 20 pagal apyvartą, be išgyvenusiųjų iškraipymo) N d. grąža > BTC -> alts, kitaip BTC.
Variantas su absoliučiu momentum: jei laimėtojo N d. grąža < 0 -> pinigai. Mokestis 0,1 %. 2018–2021 ir 2021-11 – 2026-11."""
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from xsec import load
P, V = load()
R = P.pct_change(fill_method=None)
age = P.notna().cumsum(); liq = V.rolling(30, min_periods=20).mean()
stab = [c for c in P.columns if c == "BTCUSDT"]
# altų krepšelis: top 20 pagal apyvartą (be BTC), perbalansuojama kas savaitę, lygūs svoriai
alt_r = pd.Series(0.0, P.index); members = None
for i in range(70, len(P)):
    if (i - 70) % 7 == 0:
        ok = (age.iloc[i-1] >= 60) & liq.iloc[i-1].notna(); l = liq.iloc[i-1][ok].drop(["BTCUSDT", "ETHUSDT"], errors="ignore")
        members = l.nlargest(20).index
    alt_r.iloc[i] = R.iloc[i][members].fillna(0).mean()
btc_r = R["BTCUSDT"].fillna(0); eth_r = R["ETHUSDT"].fillna(0)
def st(x, a, b):
    x = x[a:b]; e = (1 + x).cumprod(); y = len(x) / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+.1f}%/m. DD {(e / e.cummax() - 1).min() * 100:.0f}%"
alt_px = (1 + alt_r).cumprod(); btc_px = (1 + btc_r).cumprod()
for nm, x in [("BTC laikyti", btc_r), ("ETH laikyti", eth_r), ("Alts20 laikyti", alt_r)]:
    print(f"{nm}: 2018–21 {st(x, '2018-03-15', '2021-11-08')} | 2021–26 {st(x, '2021-11-08', '2026-11-14')}")
for N in [14, 30, 60, 90]:
    for absm in [False, True]:
        ma = alt_px.pct_change(N); mb = btc_px.pct_change(N)
        w = pd.Series(np.nan, P.index)
        for i in range(100, len(P), 7):
            win = "alt" if ma.iloc[i] > mb.iloc[i] else "btc"
            if absm and max(ma.iloc[i], mb.iloc[i]) < 0: win = "cash"
            w.iloc[i] = {"alt": 1, "btc": 0, "cash": -1}[win]
        w = w.ffill().shift(1)
        r = np.where(w == 1, alt_r, np.where(w == 0, btc_r, 0.0)); r = pd.Series(r, P.index)
        r -= (w.diff().fillna(0) != 0) * 0.002   # keitimas: parduoti + pirkti
        print(f"N={N:2d} {'su abs. momentum' if absm else 'be filtro      '}: 2018–21 {st(r, '2018-03-15', '2021-11-08')} | 2021–26 {st(r, '2021-11-08', '2026-11-14')} | alts dalis {(w['2021-11-08':]==1).mean():.0%}, pinigai {(w['2021-11-08':]==-1).mean():.0%}", flush=True)
