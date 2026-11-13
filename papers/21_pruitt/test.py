#!/usr/bin/env python3
"""#21 Klasikinės trendo sistemos (Pruitt, Hill „Building Winning Trading Systems with TradeStation“; Fitschen Aberration), tik long, dienos žvakės.
 - Aberration (K. Fitschen): uždarymas > SMA35 + 2σ → pirkti; uždarymas < SMA35 → parduoti.
 - King Keltner: SMA40(typical) + ATR40 pramušimas, išėjimas po SMA40.
 - Bollinger Bandit: pramušimas SMA50 + 1σ, išėjimas – slenkantis vidurkis nuo 50 d. trumpėjantis iki 10 d., jei < SMA50 − 1σ.
 - Dynamic Break Out II: kanalo ilgis 20–60 d. pagal volatilumo pokytį, Bollinger + kanalas, išėjimas po trumpėjančiu vidurkiu.
 - Thermostat: trendo režime (choppiness < 20) pramušimas 3 d. vid. + ATR; šoniniame – atšokimas (supaprastinta: tik trendo dalis).
Signalas uždarymu, sandoris kitos dienos atidarymu. Mokestis 0,1 %. Kiekviena moneta po lygią dalį."""
import os, numpy as np, pandas as pd
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/binance_1d")
G = {"BTC+ETH": ["BTC", "ETH"], "alts10": ["XRP", "BNB", "SOL", "DOGE", "ADA", "TRX", "LINK", "AVAX", "LTC", "DOT"]}
FEE = 0.001


def load(s):
    d = pd.read_csv(f"{D}/{s}USDT.csv"); d.index = pd.to_datetime(d.t, unit="ms"); return d[["o", "h", "l", "c"]]


def atr(d, n):
    tr = pd.concat([d.h - d.l, (d.h - d.c.shift()).abs(), (d.l - d.c.shift()).abs()], axis=1).max(axis=1); return tr.rolling(n).mean()


def sim(d, enter, exit_fn):
    """enter: bool Series (uždarymu); exit_fn(i, entry_i) -> bool. Pozicija nuo kitos d. atidarymo."""
    c, o = d.c.values, d.o.values; n = len(d); pos = np.zeros(n); inpos = False; ei = 0
    en = enter.fillna(False).values
    for i in range(n - 1):
        if not inpos and en[i]: inpos = True; ei = i
        elif inpos and exit_fn(i, ei): inpos = False
        pos[i + 1] = inpos
    pos = pd.Series(pos, d.index)
    r = d.c.pct_change().fillna(0)
    entry = (pos == 1) & (pos.shift(1) == 0); ex = (pos == 0) & (pos.shift(1) == 1)
    rr = pos * r
    rr[entry] = d.c[entry] / d.o[entry] - 1 - FEE
    rr[ex] = d.o[ex] / d.c.shift(1)[ex] - 1 - FEE
    return rr, pos.mean()


def aberration(d):
    m = d.c.rolling(35).mean(); s = d.c.rolling(35).std(); c = d.c.values; mv = m.values
    return sim(d, d.c > m + 2 * s, lambda i, e: c[i] < mv[i])


def king_keltner(d):
    tp = (d.h + d.l + d.c) / 3; m = tp.rolling(40).mean(); a = atr(d, 40); c = d.c.values; mv = m.values
    return sim(d, (d.c > m + a) & (m > m.shift()), lambda i, e: c[i] < mv[i])


def bollinger_bandit(d):
    m = d.c.rolling(50).mean(); s = d.c.rolling(50).std(); c = d.c.values; cs = d.c.values
    roc = d.c - d.c.shift(30)
    def ex(i, e):
        L = max(10, 50 - (i - e)); ma = cs[max(0, i - L + 1):i + 1].mean()
        return c[i] < ma and (c[i] < m.values[i] - s.values[i] or True)
    return sim(d, (d.c > m + s) & (roc > 0), ex)


def dbo2(d):
    vol = d.c.rolling(30).std(); dv = (vol / vol.shift(1)).fillna(1)
    L = pd.Series(20.0, d.index); lv = 20.0; Lv = []
    for x in dv.values:
        lv = min(60, max(20, lv * x)); Lv.append(int(round(lv)))
    Lv = np.array(Lv); c = d.c.values; h = d.h.values
    up = np.array([c[max(0, i - Lv[i] + 1):i + 1].mean() + 2 * c[max(0, i - Lv[i] + 1):i + 1].std() if i >= 20 else np.inf for i in range(len(c))])
    hh = np.array([h[max(0, i - Lv[i]):i].max() if i >= 20 else np.inf for i in range(len(c))])
    enter = pd.Series((c > up) & (c >= hh), d.index)
    def ex(i, e):
        L_ = max(10, Lv[i] - (i - e)); return c[i] < c[max(0, i - L_ + 1):i + 1].mean()
    return sim(d, enter, ex)


def thermostat(d):
    chop = (d.c - d.c.shift(30)).abs() / (d.h.rolling(30).max() - d.l.rolling(30).min()) * 100
    m3 = ((d.h + d.l + d.c) / 3).rolling(3).mean(); a = atr(d, 10); c = d.c.values; m50 = d.c.rolling(50).mean().values
    return sim(d, (chop >= 20) & (d.c > m3 + a), lambda i, e: c[i] < m50[i])


def st(r, a, b):
    r = r[a:b]; eq = (1 + r).cumprod(); y = (r.index[-1] - r.index[0]).days / 365.25
    return f"{(eq.iloc[-1] ** (1 / y) - 1) * 100:+.1f} ({(eq / eq.cummax() - 1).min() * 100:.0f})"


S = {"Aberration": aberration, "King Keltner": king_keltner, "Bollinger Bandit": bollinger_bandit, "Dynamic Break Out II": dbo2, "Thermostat (trendo dalis)": thermostat}
rows = []
for g, cs in G.items():
    data = {s: load(s) for s in cs}
    h = pd.concat({s: d.c.pct_change() for s, d in data.items()}, axis=1, sort=True)["2018":].fillna(0).mean(axis=1)
    rows.append(f"| {g} | laikyti | | {st(h, '2018-01-01', '2021-11-08')} | {st(h, '2021-11-08', '2026-11-08')} | |")
    for n, f in S.items():
        out = {s: f(d) for s, d in data.items()}
        R = pd.concat({s: o[0] for s, o in out.items()}, axis=1, sort=True)["2018":].fillna(0).mean(axis=1)
        y = (1 + R["2021-11-08":]).groupby(R["2021-11-08":].index.year).prod() - 1
        rows.append(f"| {g} | {n} | {np.mean([o[1] for o in out.values()])*100:.0f} % | {st(R, '2018-01-01', '2021-11-08')} | {st(R, '2021-11-08', '2026-11-08')} | {' '.join(f'{a}:{b*100:+.0f}' for a, b in y.items())} |")
        print(rows[-1], flush=True)
md = "| Grupė | Sistema | rinkoje | 2018–2021-11 %/m (kritimas) | 2021-11–2026-11 %/m (kritimas) | metai |\n|---|---|---|---|---|---|\n" + "\n".join(rows)
open("REZULTATAI.txt", "w").write(md + "\n")
