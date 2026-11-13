#!/usr/bin/env python3
"""#35 Zarattini, Aziz, Barbon (2024) „Beat the Market: An Effective Intraday Momentum Strategy“ (Noise Breakout) ant kripto.
Diena = 00:00 UTC. Triukšmo zona kiekvienai valandai h: open × (1 ± σ_h), σ_h = 14 d. vidurkis |close_h/open − 1|.
Kas valandą (uždarymu): kaina > viršutinė riba -> long, < apatinė -> short (variante), išėjimas grįžus į zoną (riba = max(zona, VWAP≈open)) arba 23:00 uždarymu.
Įėjimas valandos uždarymo kaina (signalas tą pačią akimirką – kaip straipsnyje). Valandiniai o/c, 0,05 % (futures) ir 0,1 %.
2018–2021-11 ir 2021-11 – 2026-11."""
import os, numpy as np, pandas as pd
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../10_sezoniskumas/data")
def prep(s):
    d = pd.read_pickle(f"{D}/{s}USDT.pkl").set_index("t"); d = d[~d.index.duplicated()]
    d["day"] = d.index.floor("D"); d["hr"] = d.index.hour
    C = d.pivot_table(index="day", columns="hr", values="c"); O = d.pivot_table(index="day", columns="hr", values="o")[0]
    C = C.dropna(); O = O.reindex(C.index)
    mv = (C.div(O, axis=0) - 1).abs()
    sig = mv.rolling(14).mean().shift(1)    # tik praėjusios dienos
    return C, O, sig
def run(C, O, sig, side, fee, mult=1.0):
    rets = []
    for day in C.index[15:]:
        o = O[day]; c = C.loc[day].values; s = sig.loc[day].values * mult
        pos = 0; entry = 0; r = 0.0
        for h in range(24):
            up, dn = o * (1 + s[h]), o * (1 - s[h])
            if pos == 1 and c[h] < up:   # grįžo į zoną
                r += c[h] / entry - 1 - 2 * fee; pos = 0
            elif pos == -1 and c[h] > dn:
                r += 1 - c[h] / entry - 2 * fee; pos = 0
            if h < 23 and pos == 0:
                if c[h] > up: pos, entry = 1, c[h]
                elif side == "ls" and c[h] < dn: pos, entry = -1, c[h]
        if pos == 1: r += c[23] / entry - 1 - 2 * fee
        if pos == -1: r += 1 - c[23] / entry - 2 * fee
        rets.append((day, r))
    return pd.Series(dict(rets))
def st(R, a, b):
    R = R[a:b]; e = (1 + R).cumprod(); y = len(R) / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+.1f}%/m. DD {(e / e.cummax() - 1).min() * 100:.0f}%"
data = {s: prep(s) for s in ["BTC", "ETH"]}
for side in ["long", "ls"]:
    for fee in [0.0005, 0.001]:
        for mult in [1.0, 1.5]:
            R = pd.concat([run(*data[s], side, fee, mult) for s in data], axis=1).fillna(0).mean(axis=1)
            y = (1 + R["2021-11-08":]).groupby(R["2021-11-08":].index.year).prod() - 1
            print(f"{side:4s} mokestis {fee*100:.2f}% zona×{mult}: 2018–21 {st(R, '2018-01-01', '2021-11-08')} | 2021–26 {st(R, '2021-11-08', '2026-11-14')} | " + " ".join(f"{k}:{v*100:+.0f}" for k, v in y.items()), flush=True)
