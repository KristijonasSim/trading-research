#!/usr/bin/env python3
"""#106 Akcijų atšokimo (pullback) sistemos S&P 500 akcijose – Connors & Alvarez.
Šaltiniai: Connors, Alvarez „Short Term Trading Strategies That Work“ (2008) – RSI(2) < 5 virš SMA200, išeiti kai close > SMA5;
Connors, Alvarez, Radtke „ConnorsRSI“ (2012) – CRSI(3,2,100) < 5…15 virš SMA200, išeiti kai CRSI > 70;
„didelis dienos kritimas“ (Connors „How Markets Really Work“: pirkti po stiprių kritimų) – dienos grąža < −5 % virš SMA200, išeiti close > SMA5 arba po 10 d.
Iš tuo metu indekse esančių akcijų (fja05680/sp500, Yahoo uždarymo kainos), rikiuojama pagal žemiausią rodiklį, K vietų po 1/K kapitalo.
Vykdymas: MOC (signalas ir įėjimas tos dienos uždarymu – optimistiška) arba kitos dienos uždarymu. Kaštai 0,1 % į vieną pusę.
Svertas L: skolinta dalis kainuoja 5 %/m. Ribotumas: iki ~2014 Yahoo neturi dalies iš indekso išėjusių akcijų (rezultatai per geri)."""
import os, sys, numpy as np, pandas as pd
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../07_lowvol"))
exec(open("test.py").read().split("W = {")[0])
C = C[C.index >= "2003-01-01"]; spy = spy[C.index]; R = C.pct_change(fill_method=None)
days = C.index[C.index >= "2005-01-01"]

def rsi(x, n):
    d = x.diff(); u = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(); v = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + u / v)
sma200 = C.rolling(200).mean(); sma5 = C.rolling(5).mean()
rsi2 = rsi(C, 2)
# ConnorsRSI: RSI(3) kainos, RSI(2) serijos, 100 d. procentilis dienos grąžos
sgn = np.sign(C.diff()).fillna(0).values; st = np.zeros_like(sgn)
for i in range(1, len(sgn)):
    s = sgn[i]; p = st[i - 1]
    st[i] = np.where(s == 0, 0, np.where(np.sign(p) == s, p + s, s))
streak = pd.DataFrame(st, C.index, C.columns); streak[C.isna()] = np.nan
pr = R.rolling(100).apply(lambda a: (a[:-1] < a[-1]).mean() * 100, raw=True) if os.environ.get("CRSI") else None
crsi = (rsi(C, 3) + rsi(streak, 2) + pr) / 3 if pr is not None else None
mem = {}
for dt in days:
    mem[dt] = set(members(dt))
spy_up = spy > spy.rolling(200).mean()
Cv, S200, S5, Rv = C.values, sma200.values, sma5.values, R.values
cols = list(C.columns); ix = {d: i for i, d in enumerate(C.index)}
memmask = np.zeros(C.shape, bool)
for dt in days:
    i = ix[dt]; memmask[i] = [c in mem[dt] for c in cols]

def run(kind="rsi2", thr=5, K=10, L=1.0, moc=True, filt=False, fee=0.001, maxhold=None):
    if kind == "rsi2": score = rsi2.values; ent = score < thr
    elif kind == "crsi": score = crsi.values; ent = score < thr
    else: score = Rv; ent = Rv < -thr / 100
    ent = ent & (Cv > S200) & memmask
    pos = {}  # col -> (entry_idx)
    eq = 1.0; out = []; d0 = ix[days[0]]
    for i in range(d0, len(C.index)):
        # dienos grąža laikomoms pozicijoms
        if pos:
            r = np.nansum([Rv[i, c] for c in pos]) / K
            eq *= 1 + L * r - (L - 1) * 0.05 / 252 * (len(pos) / K)
        # išėjimai šios dienos uždarymu
        for c in list(pos):
            done = Cv[i, c] > S5[i, c] if kind != "crsi" else crsi.values[i, c] > 70
            if maxhold and i - pos[c] >= maxhold: done = True
            if np.isnan(Cv[i, c]): done = True
            if done: del pos[c]; eq *= 1 - fee * L / K
        # įėjimai: signalas dienos i (MOC) arba i-1 (kitos dienos uždarymu)
        j = i if moc else i - 1
        if len(pos) < K and (not filt or spy_up.iloc[j]):
            cand = np.where(ent[j])[0]
            cand = [c for c in cand if c not in pos and not np.isnan(Cv[i, c])]
            cand.sort(key=lambda c: score[j, c])
            for c in cand[:K - len(pos)]:
                pos[c] = i; eq *= 1 - fee * L / K
        out.append(eq)
    return pd.Series(out, C.index[d0:])

def stat(e, a, b):
    e = e[a:b]; y = len(e) / 252; c = (e.iloc[-1] / e.iloc[0]) ** (1 / y) - 1
    return f"{c*100:+6.1f}% DD {(e / e.cummax() - 1).min()*100:4.0f}%"
def years(e):
    y = e.groupby(e.index.year).last(); y = y / y.shift(1).fillna(e.iloc[0]) - 1
    return " ".join(f"{k%100:02d}:{v*100:+.0f}" for k, v in y.items())
spye = (1 + spy.pct_change().fillna(0))[days].cumprod()
print("SPY            ", "2005–14", stat(spye, "2005", "2014"), "| 2015–26", stat(spye, "2015", "2027"), "|", years(spye), flush=True)
grid = [("rsi2", 5), ("rsi2", 2), ("drop", 5), ("drop", 8)] + ([("crsi", 5), ("crsi", 10)] if crsi is not None else [])
for kind, thr in grid:
    for K in (5, 10):
        for moc in (True, False):
            for filt in (False, True):
                e = run(kind, thr, K, 1.0, moc, filt, maxhold=10 if kind == "drop" else None)
                print(f"{kind}<{thr} K={K} {'MOC ' if moc else 'kitą'} {'SPY>200' if filt else '       '}: 2005–14 {stat(e,'2005','2014')} | 2015–26 {stat(e,'2015','2027')} | {years(e)}", flush=True)
