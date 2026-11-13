#!/usr/bin/env python3
"""#23 Klasikinės publikuotos sistemos ant kripto (dienos, tik long, mokestis 0,1 %, signalas uždarymu → kitos d. atidarymas):
 - Darvas dėžė (N. Darvas 1960): naujas 52 sav. maksimumas, dėžė = 3 d. nepramušta viršūnė/dugnas; pirkti virš dėžės, stop dėžės dugne.
 - Holy Grail (L. Raschke, „Street Smarts“ 1995): ADX14 > 30, kaina atsitraukia iki EMA20 → pirkti virš tos dienos maksimumo; išėjimas – naujas 20 d. maksimumas ar stop po atsitraukimo minimumu.
 - Turtle Soup (Raschke): naujas 20 d. minimumas (ankstesnis ≥ 3 d. senumo), uždarymas grįžta virš → pirkti; išėjimas po 5 d. arba stop.
 - Parabolic SAR (J. W. Wilder 1978): long, kai kaina virš SAR.
 - Alligator (B. Williams): lūpos > dantys > žandikaulis (SMMA 5/8/13 su poslinkiu).
 - Seykota EMA kryžius: EMA15 > EMA150 (E. Seykota, „Market Wizards“)."""
import os, numpy as np, pandas as pd
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/binance_1d")
G = {"BTC+ETH": ["BTC", "ETH"], "alts10": ["XRP", "BNB", "SOL", "DOGE", "ADA", "TRX", "LINK", "AVAX", "LTC", "DOT"]}
FEE = 0.001
def load(s):
    d = pd.read_csv(f"{D}/{s}USDT.csv"); d.index = pd.to_datetime(d.t, unit="ms"); return d[["o", "h", "l", "c"]]
def from_state(d, st_):
    pos = pd.Series(st_, d.index).astype(float).shift(1).fillna(0)
    r = d.c.pct_change().fillna(0)
    entry = (pos == 1) & (pos.shift(1) == 0); ex = (pos == 0) & (pos.shift(1) == 1)
    rr = pos * r; rr[entry] = d.c[entry] / d.o[entry] - 1 - FEE; rr[ex] = d.o[ex] / d.c.shift(1)[ex] - 1 - FEE
    return rr
def stop_sim(d, entry_level, stop_level, exit_cond, max_hold=None):
    """įėjimas dienos viduje stop orderiu ties entry_level (nustatytas vakar), stop ties stop_level (fiksuojamas įėjus)."""
    o, h, l, c = d.o.values, d.h.values, d.l.values, d.c.values; n = len(d); r = np.zeros(n); inpos = False; stop = 0; ei = 0
    el = entry_level.values; sl = stop_level.values; xc = exit_cond.fillna(False).values
    for i in range(1, n):
        if not inpos:
            lvl = el[i - 1]
            if not np.isnan(lvl) and h[i] > lvl:
                px = max(o[i], lvl); stop = sl[i - 1]; inpos = True; ei = i
                if l[i] < stop and stop < px: r[i] = stop / px - 1 - 2 * FEE; inpos = False
                else: r[i] = c[i] / px - 1 - FEE
        else:
            if l[i] < stop: r[i] = min(o[i], stop) / c[i - 1] - 1 - FEE; inpos = False
            elif xc[i - 1] or (max_hold and i - ei >= max_hold): r[i] = o[i] / c[i - 1] - 1 - FEE; inpos = False
            else: r[i] = c[i] / c[i - 1] - 1
    return pd.Series(r, d.index)
def adx(d, n=14):
    up = d.h.diff(); dn = -d.l.diff()
    pdm = np.where((up > dn) & (up > 0), up, 0); ndm = np.where((dn > up) & (dn > 0), dn, 0)
    tr = pd.concat([d.h - d.l, (d.h - d.c.shift()).abs(), (d.l - d.c.shift()).abs()], axis=1).max(axis=1)
    a = tr.ewm(alpha=1 / n).mean(); pdi = 100 * pd.Series(pdm, d.index).ewm(alpha=1 / n).mean() / a; ndi = 100 * pd.Series(ndm, d.index).ewm(alpha=1 / n).mean() / a
    return (100 * (pdi - ndi).abs() / (pdi + ndi)).ewm(alpha=1 / n).mean()
def darvas(d):
    hi52 = d.h.rolling(252, min_periods=120).max()
    top = d.h.rolling(4).max(); bot = d.l.rolling(4).min()
    new = d.h >= hi52
    box_top = top.where(new).ffill(); box_bot = bot.where(new).ffill()
    return stop_sim(d, box_top, box_bot, d.c < d.l.rolling(20).min().shift(1))
def holy_grail(d):
    e = d.c.ewm(span=20).mean(); a = adx(d)
    setup = (a > 30) & (d.l <= e) & (d.c.rolling(20).max().shift(1) > e * 1.02)
    lvl = d.h.where(setup)
    return stop_sim(d, lvl, d.l.where(setup), d.h >= d.h.rolling(20).max())
def turtle_soup(d):
    ll = d.l.rolling(20).min().shift(1); old = d.l.rolling(20).apply(np.argmin, raw=True).shift(1) <= 16
    setup = (d.l < ll) & old & (d.c > ll)
    return stop_sim(d, d.h.where(setup), d.l.where(setup), pd.Series(False, d.index), max_hold=5)
def psar(d, af0=0.02, afmax=0.2):
    h, l = d.h.values, d.l.values; n = len(d); sar = np.zeros(n); up = True; ep = h[0]; af = af0; sar[0] = l[0]; st_ = np.zeros(n)
    for i in range(1, n):
        sar[i] = sar[i - 1] + af * (ep - sar[i - 1])
        if up:
            sar[i] = min(sar[i], l[i - 1], l[i - 2] if i > 1 else l[i - 1])
            if l[i] < sar[i]: up = False; sar[i] = ep; ep = l[i]; af = af0
            elif h[i] > ep: ep = h[i]; af = min(afmax, af + af0)
        else:
            sar[i] = max(sar[i], h[i - 1], h[i - 2] if i > 1 else h[i - 1])
            if h[i] > sar[i]: up = True; sar[i] = ep; ep = h[i]; af = af0
            elif l[i] < ep: ep = l[i]; af = min(afmax, af + af0)
        st_[i] = up
    return from_state(d, st_)
def alligator(d):
    m = (d.h + d.l) / 2; sm = lambda n, s: m.ewm(alpha=1 / n).mean().shift(s)
    return from_state(d, ((sm(5, 3) > sm(8, 5)) & (sm(8, 5) > sm(13, 8))).values)
def seykota(d):
    return from_state(d, (d.c.ewm(span=15).mean() > d.c.ewm(span=150).mean()).values)
def st(r, a, b):
    r = r[a:b]; eq = (1 + r).cumprod(); y = (r.index[-1] - r.index[0]).days / 365.25
    return f"{(eq.iloc[-1] ** (1 / y) - 1) * 100:+.1f} ({(eq / eq.cummax() - 1).min() * 100:.0f})"
S = {"Darvas dėžė": darvas, "Holy Grail (Raschke)": holy_grail, "Turtle Soup (Raschke)": turtle_soup, "Parabolic SAR": psar, "Alligator": alligator, "Seykota EMA15/150": seykota}
rows = []
for g, cs in G.items():
    data = {s: load(s) for s in cs}
    for n, f in S.items():
        R = pd.concat({s: f(d) for s, d in data.items()}, axis=1, sort=True)["2018":].fillna(0).mean(axis=1)
        y = (1 + R["2021-11-08":]).groupby(R["2021-11-08":].index.year).prod() - 1
        rows.append(f"| {g} | {n} | {st(R, '2018-01-01', '2021-11-08')} | {st(R, '2021-11-08', '2026-11-08')} | {' '.join(f'{a}:{b*100:+.0f}' for a, b in y.items())} |"); print(rows[-1], flush=True)
open("REZULTATAI.txt", "w").write("| Grupė | Sistema | 2018–2021-11 %/m (kritimas) | 2021-11–2026-11 | metai |\n|---|---|---|---|---|\n" + "\n".join(rows) + "\n")
