#!/usr/bin/env python3
"""#107 Connors & Alvarez „High Probability ETF Trading“ (2009): 7 atšokimo sistemos ant 3x ETF.
Signalas skaičiuojamas iš bazinio ETF (QQQ, SPY, IWM, SOXX, XLK), prekiaujama 3x versija (TQQQ, UPRO, TNA, SOXL, TECL).
3x kaina – sintetinė (3 × bazinė grąža − 2 × trumpųjų palūkanų − 0,95 %/m.), kad būtų 2001–2009 (prieš paskelbimą, su 2008);
2010+ palyginama su tikrais 3x ETF. Sistemos (visos tik kai close > SMA200):
 3HL  – 3 d. iš eilės žemesnis high ir low, close < SMA5; išeiti close > SMA5
 RSI25 – RSI(4) < 25; išeiti RSI(4) > 55
 R3   – RSI(2) krenta 3 d. iš eilės, 1-ą d. < 60, šiandien < 10; išeiti RSI(2) > 70
 PB   – %b(20,2) < 0,2 tris d. iš eilės; išeiti %b > 0,8
 MDD  – 4 iš 5 paskutinių d. žemyn, close < SMA5; išeiti close > SMA5
 RSI6 – RSI(2) < 6; išeiti close > SMA5
 TPS  – RSI(2) < 25 dvi d. iš eilės: 10 % pozicijos, papildyti 20/30/40 % kiekvieno žemesnio uždarymo; išeiti RSI(2) > 70
Vykdymas: MOC (tos dienos uždarymu, kaip knygoje) arba kitos dienos uždarymu. Kaštai 0,1 % į vieną pusę. Ne pozicijoje – BIL."""
import os, numpy as np, pandas as pd
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
L = lambda t: pd.read_csv(f"{D}/{t}.csv", index_col=0, parse_dates=True)
PAIRS = [("QQQ", "TQQQ"), ("SPY", "UPRO"), ("IWM", "TNA"), ("SOXX", "SOXL"), ("XLK", "TECL")]
irx = L("IRX").Close / 100 / 252
def rsi(x, n):
    d = x.diff(); u = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(); v = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + u / v)
def signals(b):
    c, h, l = b.Close, b.High, b.Low; s200 = c.rolling(200).mean(); s5 = c.rolling(5).mean(); up = c > s200
    r2, r4 = rsi(c, 2), rsi(c, 4); m = c.rolling(20).mean(); sd = c.rolling(20).std(); pb = (c - (m - 2 * sd)) / (4 * sd)
    dn = (c.diff() < 0).astype(int)
    E = {"3HL": up & (c < s5) & (h < h.shift()) & (h.shift() < h.shift(2)) & (h.shift(2) < h.shift(3)) & (l < l.shift()) & (l.shift() < l.shift(2)) & (l.shift(2) < l.shift(3)),
         "RSI25": up & (r4 < 25),
         "R3": up & (r2 < r2.shift()) & (r2.shift() < r2.shift(2)) & (r2.shift(2) < r2.shift(3)) & (r2.shift(2) < 60) & (r2 < 10),
         "PB": up & (pb < 0.2) & (pb.shift() < 0.2) & (pb.shift(2) < 0.2),
         "MDD": up & (c < s5) & (dn.rolling(5).sum() >= 4),
         "RSI6": up & (r2 < 6),
         "TPS": up & (r2 < 25) & (r2.shift() < 25)}
    X = {"3HL": c > s5, "RSI25": r4 > 55, "R3": r2 > 70, "PB": pb > 0.8, "MDD": c > s5, "RSI6": c > s5, "TPS": r2 > 70}
    return E, X, c
def run(base, sysn, moc=True, fee=0.001, real=None):
    b = L(base); E, X, c = signals(b)
    rb = c.pct_change(); rf = irx.reindex(c.index).ffill().fillna(0)
    r3 = 3 * rb - 2 * rf - 0.0095 / 252 if real is None else L(real).Close.pct_change().reindex(c.index)
    e, x = E[sysn].values, X[sysn].values; cv = c.values; w = 0.0; W = np.zeros(len(c)); last = None
    for i in range(len(c)):
        j = i if moc else i - 1
        if j < 0: continue
        if w > 0 and x[j]: w = 0.0; last = None
        elif sysn == "TPS":
            if w == 0 and e[j]: w = 0.1; last = cv[j]
            elif 0 < w < 1 and cv[j] < last: w = min(1.0, w + {0.1: 0.2, 0.3: 0.3, 0.6: 0.4}.get(round(w, 1), 0)); last = cv[j]
        elif w == 0 and e[j]: w = 1.0
        W[i] = w
    W = pd.Series(W, c.index)  # pozicija nuo dienos i uždarymo -> grąža i+1
    held = W.shift(1).fillna(0)
    ret = held * r3.fillna(0) + (1 - held) * rf - W.diff().abs().fillna(0) * fee
    return ret, held
def stat(r, a, b):
    r = r[a:b].dropna(); e = (1 + r).cumprod(); y = len(r) / 252
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+6.1f}% DD {(e / e.cummax() - 1).min() * 100:4.0f}%"
def yrs(r, a="2020"):
    r = r[a:]; y = (1 + r).groupby(r.index.year).prod() - 1
    return " ".join(f"{k % 100:02d}:{v * 100:+.0f}" for k, v in y.items())
P = [("2001", "2009"), ("2010", "2019"), ("2020", "2026")]
print("periodai: 2001–09 (prieš knygą) | 2010–19 | 2020–26 | metai 2020+")
for base, lev in PAIRS:
    rb = L(base).Close.pct_change(); rf = irx.reindex(rb.index).ffill().fillna(0); r3 = 3 * rb - 2 * rf - 0.0095 / 252
    print(f"\n== {lev} (signalas {base}) | laikyti 3x: " + " | ".join(stat(r3, a, b) for a, b in P) + f" | laikyti {base}: " + " | ".join(stat(rb, a, b) for a, b in P))
    for s in ["3HL", "RSI25", "R3", "PB", "MDD", "RSI6", "TPS"]:
        for moc in (True, False):
            r, h = run(base, s, moc)
            print(f"{s:5s} {'MOC ' if moc else 'kitą'}: " + " | ".join(stat(r, a, b) for a, b in P) + f" | rinkoje {h['2010':].mean() * 100:3.0f}% | {yrs(r)}")
        rr, _ = run(base, s, True, real=lev)
        print(f"{s:5s} tikras {lev} MOC 2010–19 {stat(rr, '2010', '2019')} | 2020–26 {stat(rr, '2020', '2026')}")
