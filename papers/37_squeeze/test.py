#!/usr/bin/env python3
"""#37 John Carter „Mastering the Trade“ (2005) TTM Squeeze ir Bollinger „Squeeze“ (Bollinger on Bollinger Bands, 2001), kripto 1d, tik long.
TTM: squeeze = BB(20,2) viduje Keltner(20,1.5×ATR); kai squeeze išsijungia ir momentum (close − vid(Donchian20, SMA20)) > 0 ir kyla -> pirkti;
išeiti kai momentum pradeda kristi (2 d. iš eilės) arba < 0.
Bollinger: BB plotis 6 mėn. minimume -> pirkti pramušus viršutinę juostą, išeiti žemiau vidurio.
Pozicija nuo kitos dienos, 0,1 % mokestis. 2018–2021-11 ir 2021-11 – 2026-11."""
import os, numpy as np, pandas as pd
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/binance_1d")
G = {"BTC+ETH": ["BTC", "ETH"], "alts10": ["XRP", "BNB", "SOL", "DOGE", "ADA", "TRX", "LINK", "AVAX", "LTC", "DOT"]}
def load(s):
    d = pd.read_csv(f"{D}/{s}USDT.csv"); d.index = pd.to_datetime(d.t, unit="ms"); return d[["o", "h", "l", "c"]]
def ttm(d, kc=1.5):
    c = d.c; m = c.rolling(20).mean(); sd = c.rolling(20).std()
    tr = pd.concat([d.h - d.l, (d.h - c.shift()).abs(), (d.l - c.shift()).abs()], axis=1).max(axis=1); atr = tr.rolling(20).mean()
    sq = (m + 2 * sd < m + kc * atr) & (m - 2 * sd > m - kc * atr)
    mom = c - ((d.h.rolling(20).max() + d.l.rolling(20).min()) / 2 + m) / 2
    mom = mom.rolling(20).apply(lambda a: np.polyval(np.polyfit(np.arange(20), a, 1), 19), raw=True)  # linreg kaip originale
    fired = sq.shift(1).fillna(False).astype(bool) & ~sq
    pos = np.zeros(len(d)); inpos = False
    for i in range(40, len(d)):
        if not inpos and fired.iloc[i] and mom.iloc[i] > 0 and mom.iloc[i] > mom.iloc[i-1]: inpos = True
        elif inpos and (mom.iloc[i] < 0 or (mom.iloc[i] < mom.iloc[i-1] and mom.iloc[i-1] < mom.iloc[i-2])): inpos = False
        pos[i] = inpos
    return pd.Series(pos, d.index)
def bbsq(d, look=125):
    c = d.c; m = c.rolling(20).mean(); sd = c.rolling(20).std(); w = 4 * sd / m
    low = w <= w.rolling(look).min() * 1.1
    pos = np.zeros(len(d)); inpos = False; armed = 0
    for i in range(look, len(d)):
        if low.iloc[i]: armed = 10
        if not inpos and armed > 0 and c.iloc[i] > m.iloc[i] + 2 * sd.iloc[i]: inpos = True
        elif inpos and c.iloc[i] < m.iloc[i]: inpos = False
        armed -= 1; pos[i] = inpos
    return pd.Series(pos, d.index)
def ret(d, pos):
    p = pos.shift(1).fillna(0); return p * d.c.pct_change().fillna(0) - p.diff().abs().fillna(0) * 0.001
def st(x, a, b):
    x = x[a:b]; e = (1 + x).cumprod(); y = len(x) / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+.1f}%/m. DD {(e / e.cummax() - 1).min() * 100:.0f}%"
data = {s: load(s) for g in G.values() for s in g}
for g, syms in G.items():
    for nm, f in [("TTM kc1.5", lambda d: ttm(d, 1.5)), ("TTM kc2.0", lambda d: ttm(d, 2.0)), ("BB squeeze 6 mėn.", lambda d: bbsq(d, 125)), ("BB squeeze 3 mėn.", lambda d: bbsq(d, 63))]:
        pos = {s: f(data[s]) for s in syms}
        x = pd.concat([ret(data[s], pos[s]) for s in syms], axis=1, sort=True)["2018":].fillna(0).mean(axis=1)
        n = int(sum((pos[s].diff() == 1)["2021-11-08":].sum() for s in syms))
        y = (1 + x["2021-11-08":]).groupby(x["2021-11-08":].index.year).prod() - 1
        print(f"{g} {nm}: {st(x, '2018-01-01', '2021-11-08')} | {st(x, '2021-11-08', '2026-11-14')} | sand. {n} | " + " ".join(f"{k}:{v*100:+.0f}" for k, v in y.items()), flush=True)
