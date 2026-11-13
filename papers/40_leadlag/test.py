#!/usr/bin/env python3
"""#40 BTC → altcoin'ų vėlavimas (lead-lag; pvz., Guo, Härdle, Tao 2022 „Lead-lag in crypto“; Sifat ir kt. 2019).
Jei BTC per paskutinę valandą pakilo (nukrito) > X, kitą valandą long (short) altcoin'ų krepšelį (ETH, BNB, XRP, ADA, LINK, LTC, TRX).
Valandiniai o/c, mokestis 0,05 %/pusė (futures). Taip pat koreliacija be mokesčių. 2018–2021-11 ir 2021-11 – 2026-11."""
import os, numpy as np, pandas as pd
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../10_sezoniskumas/data")
def ld(s):
    d = pd.read_pickle(f"{D}/{s}USDT.pkl").set_index("t"); d = d[~d.index.duplicated()]; return d.c / d.o - 1
A = ["ETH", "BNB", "XRP", "ADA", "LINK", "LTC", "TRX"]
btc = ld("BTC"); alts = pd.DataFrame({s: ld(s) for s in A}).reindex(btc.index)
alt = alts.mean(axis=1)
print("koreliacija BTC(t) su altais(t+1):", round(btc.corr(alt.shift(-1)), 4), "| altai(t) su altais(t+1):", round(alt.corr(alt.shift(-1)), 4))
def st(x, a, b):
    x = x[a:b].fillna(0); e = (1 + x).cumprod(); y = len(x) / (365.25 * 24)
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+.1f}%/m. DD {(e / e.cummax() - 1).min() * 100:.0f}%"
for X in [0.005, 0.01, 0.02, 0.03]:
    for side in ["long", "ls"]:
        for fee in [0.0, 0.0005]:
            p = np.where(btc > X, 1, np.where((btc < -X) & (side == "ls"), -1, 0)); p = pd.Series(p, btc.index).shift(1).fillna(0)
            x = p * alt - p.abs() * 2 * fee
            print(f"X={X*100:.1f}% {side:4s} mok. {fee*100:.2f}%: 2018–21 {st(x, '2018-01-01', '2021-11-08')} | 2021–26 {st(x, '2021-11-08', '2026-11-14')} | sandorių/m. {int(p['2021-11-08':].abs().sum()/5)}", flush=True)
