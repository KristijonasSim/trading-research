"""94: Jesse (jesse-ai/example-strategies) dar netestuotos: KDJ (K kerta D aukštyn, J < 20 -> long; atvirkščiai -> išeiti/short),
IFR2 (Brazilijos „IFR2“: RSI(2) < 25 ir kaina > SMA50 -> pirkti, išeiti kai uždarymas > 2 ankstesnių barų aukščiausio),
SimpleBollinger (uždarymas > viršutinė BB(20,2) -> long, išeiti kai < vidurinė). BTC+ETH ir alts10, 4h ir 1d, long-only 0,1 % ir long+short 0,05 %.
Signalas uždarymu, pozicija nuo kito baro. Paleisti: freqtrade/.venv/bin/python papers/94_jesse_examples/test.py"""
import os, numpy as np, pandas as pd
R = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "freqtrade/user_data/data/binance")
def rsi(x, n):
    d = x.diff(); u = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean(); v = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean(); return 100 - 100/(1 + u/v)
def state(ent, ex, ents=None, exs=None):
    pos = np.zeros(len(ent)); cur = 0
    for i in range(len(ent)):
        if cur == 1 and ex[i]: cur = 0
        if cur == -1 and exs is not None and exs[i]: cur = 0
        if cur == 0: cur = 1 if ent[i] else (-1 if ents is not None and ents[i] else 0)
        pos[i] = cur
    return pos
def kdj(d):
    lo, hi = d.low.rolling(9).min(), d.high.rolling(9).max(); rsv = (d.close - lo) / (hi - lo) * 100
    k = rsv.ewm(alpha=1/3, adjust=False).mean(); dd = k.ewm(alpha=1/3, adjust=False).mean(); j = 3 * k - 2 * dd
    up = (k > dd) & (k.shift() <= dd.shift()); dn = (k < dd) & (k.shift() >= dd.shift())
    return state((up & (j < 20)).values, dn.values, (dn & (j > 80)).values, up.values)
def ifr2(d):
    r2 = rsi(d.close, 2); s = d.close.rolling(50).mean(); ex = d.close > d.high.shift(1).rolling(2).max()
    exs = d.close < d.low.shift(1).rolling(2).min()
    return state(((r2 < 25) & (d.close > s)).values, ex.values, ((r2 > 75) & (d.close < s)).values, exs.values)
def sboll(d):
    m = d.close.rolling(20).mean(); sd = d.close.rolling(20).std(); up, lo = m + 2 * sd, m - 2 * sd
    return state((d.close > up).values, (d.close < m).values, (d.close < lo).values, (d.close > m).values)
IND = {"KDJ": kdj, "IFR2": ifr2, "SimpleBollinger": sboll}
def ret(d, s, mode):
    s = pd.Series(s, d.index).fillna(0); pos = s.clip(lower=0) if mode == "long" else s; fee = 0.001 if mode == "long" else 0.0005
    r = d.close.pct_change().fillna(0); p1 = pos.shift(1).fillna(0)
    return pd.Series((p1 * r - pos.diff().abs().fillna(0) * fee).values, d.date)
def st(x, a, b):
    x = x[(x.index >= pd.Timestamp(a, tz="UTC")) & (x.index < pd.Timestamp(b, tz="UTC"))]; e = (1 + x).cumprod(); y = (x.index[-1] - x.index[0]).days / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+6.1f}% kr {(e / e.cummax() - 1).min() * 100:4.0f}%"
PER = [("2018-06-01", "2022-01-01"), ("2022-01-01", "2027-01-01")]
ALTS = "XRP BNB SOL DOGE ADA TRX LINK AVAX LTC DOT".split()
print("periodai: 2018-06–21 | 2022–26")
for tf in ("4h", "1d"):
    data = {c: pd.read_feather(f"{R}/{c}_USDT-{tf}.feather") for c in ["BTC", "ETH"] + ALTS}
    for nm, f in IND.items():
        sig = {c: f(d) for c, d in data.items()}
        for mode in ("long", "ls"):
            be = pd.concat([ret(data[c], sig[c], mode) for c in ("BTC", "ETH")], axis=1, sort=True).fillna(0).mean(axis=1)
            al = pd.concat([ret(data[c], sig[c], mode) for c in ALTS], axis=1, sort=True).fillna(0).mean(axis=1)
            print(f"{tf} {nm:16s} {mode:4s}: BTC+ETH {' | '.join(st(be, a, b) for a, b in PER)} || alts10 {' | '.join(st(al, a, b) for a, b in PER)}", flush=True)
