#!/usr/bin/env python3
"""#38 Populiariausi TradingView viešieji indikatoriai kaip strategijos (tik long, kripto 1d, 0,1 %):
 - UT Bot Alerts (QuantNomad / Yo_adriiiiaan): ATR trailing stop (a=1..2, ATR10), pirkti kai close kerta stop'ą aukštyn;
 - WaveTrend (LazyBear): pirkti kai WT1 kerta WT2 aukštyn žemiau −53 (perparduota) arba bet kur; išeiti kerta žemyn;
 - SSL Channel (Erwin Beckers): SMA(high,10)/SMA(low,10) kanalas, long kai close > viršutinė;
 - QQE (Igor Livshin): RSI(14) EMA5 ir QQE linija (4,236×ATR RSI), long kai RSIMA > QQE linija.
Pozicija nuo kitos dienos. 2018–2021-11 ir 2021-11 – 2026-11."""
import os, numpy as np, pandas as pd
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/binance_1d")
G = {"BTC+ETH": ["BTC", "ETH"], "alts10": ["XRP", "BNB", "SOL", "DOGE", "ADA", "TRX", "LINK", "AVAX", "LTC", "DOT"]}
def load(s):
    d = pd.read_csv(f"{D}/{s}USDT.csv"); d.index = pd.to_datetime(d.t, unit="ms"); return d[["o", "h", "l", "c"]]
def atr(d, n):
    tr = pd.concat([d.h - d.l, (d.h - d.c.shift()).abs(), (d.l - d.c.shift()).abs()], axis=1).max(axis=1); return tr.ewm(alpha=1/n, adjust=False).mean()
def utbot(d, a=1.0, n=10):
    c = d.c.values; nl = (a * atr(d, n)).values; ts = np.zeros(len(c)); pos = np.zeros(len(c))
    for i in range(1, len(c)):
        p = ts[i-1]
        if c[i] > p and c[i-1] > p: ts[i] = max(p, c[i] - nl[i])
        elif c[i] < p and c[i-1] < p: ts[i] = min(p, c[i] + nl[i])
        elif c[i] > p: ts[i] = c[i] - nl[i]
        else: ts[i] = c[i] + nl[i]
        pos[i] = 1 if c[i] > ts[i] else 0
    return pd.Series(pos, d.index)
def wavetrend(d, os_lvl=None):
    ap = (d.h + d.l + d.c) / 3; esa = ap.ewm(span=10, adjust=False).mean(); dd = (ap - esa).abs().ewm(span=10, adjust=False).mean()
    ci = (ap - esa) / (0.015 * dd); wt1 = ci.ewm(span=21, adjust=False).mean(); wt2 = wt1.rolling(4).mean()
    up = (wt1 > wt2) & (wt1.shift() <= wt2.shift()); dn = (wt1 < wt2) & (wt1.shift() >= wt2.shift())
    if os_lvl is not None: up &= wt1 < os_lvl
    pos = np.zeros(len(d)); inp = False
    for i in range(len(d)):
        if up.iloc[i]: inp = True
        elif dn.iloc[i]: inp = False
        pos[i] = inp
    return pd.Series(pos, d.index)
def ssl(d, n=10):
    hi = d.h.rolling(n).mean(); lo = d.l.rolling(n).mean(); pos = np.zeros(len(d)); hlv = 0
    for i in range(n, len(d)):
        hlv = 1 if d.c.iloc[i] > hi.iloc[i] else (-1 if d.c.iloc[i] < lo.iloc[i] else hlv); pos[i] = hlv == 1
    return pd.Series(pos, d.index)
def qqe(d, rsi_n=14, sf=5, k=4.236):
    dl = d.c.diff(); up = dl.clip(lower=0).ewm(alpha=1/rsi_n, adjust=False).mean(); dn = (-dl.clip(upper=0)).ewm(alpha=1/rsi_n, adjust=False).mean()
    rsi = 100 - 100 / (1 + up / dn); rm = rsi.ewm(span=sf, adjust=False).mean()
    atr_rsi = rm.diff().abs(); dar = atr_rsi.ewm(span=2*rsi_n-1, adjust=False).mean().ewm(span=2*rsi_n-1, adjust=False).mean() * k
    r = rm.values; dv = dar.values; line = np.zeros(len(r)); pos = np.zeros(len(r))
    for i in range(1, len(r)):
        if np.isnan(r[i]) or np.isnan(dv[i]): continue
        lb, ub = r[i] - dv[i], r[i] + dv[i]; p = line[i-1]
        if r[i-1] > p and r[i] > p: line[i] = max(p, lb)
        elif r[i-1] < p and r[i] < p: line[i] = min(p, ub)
        elif r[i] > p: line[i] = lb
        else: line[i] = ub
        pos[i] = r[i] > line[i]
    return pd.Series(pos, d.index)
def ret(d, pos):
    p = pos.shift(1).fillna(0); return p * d.c.pct_change().fillna(0) - p.diff().abs().fillna(0) * 0.001
def st(x, a, b):
    x = x[a:b]; e = (1 + x).cumprod(); y = len(x) / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+.1f}%/m. DD {(e / e.cummax() - 1).min() * 100:.0f}%"
data = {s: load(s) for g in G.values() for s in g}
tests = [("UT Bot a=1", lambda d: utbot(d, 1)), ("UT Bot a=2", lambda d: utbot(d, 2)), ("UT Bot a=3", lambda d: utbot(d, 3)),
         ("WaveTrend", lambda d: wavetrend(d)), ("WaveTrend <−53", lambda d: wavetrend(d, -53)),
         ("SSL 10", lambda d: ssl(d, 10)), ("SSL 20", lambda d: ssl(d, 20)), ("QQE", lambda d: qqe(d))]
for g, syms in G.items():
    for nm, f in tests:
        pos = {s: f(data[s]) for s in syms}
        x = pd.concat([ret(data[s], pos[s]) for s in syms], axis=1, sort=True)["2018":].fillna(0).mean(axis=1)
        n = int(sum((pos[s].diff() == 1)["2021-11-08":].sum() for s in syms))
        y = (1 + x["2021-11-08":]).groupby(x["2021-11-08":].index.year).prod() - 1
        print(f"{g} {nm}: {st(x, '2018-01-01', '2021-11-08')} | {st(x, '2021-11-08', '2026-11-14')} | sand. {n} | " + " ".join(f"{k}:{v*100:+.0f}" for k, v in y.items()), flush=True)
