"""77: YouTube/TradingView klasika: MACD kirtimas virš/žemiau 200 EMA (TP 1,5R, SL už 200 EMA arba 14 barų žemumos), Stoch RSI kirtimas trendo kryptimi
(kaina > EMA200, K kerta D iš < 20; išėjimas K > 80), Williams Alligator (5/8/13 SMMA, laikyti kai lūpos > dantys > žandikaulis), Heikin Ashi (2 žalios iš eilės
virš EMA50 -> long, raudona -> išeiti), 9/21 EMA kirtimas. BTC+ETH ir alts10, 1h/4h/1d, long-only spot 0,1 % ir long+short perp 0,05 %.
Signalas uždarymu, pozicija nuo kito baro. Paleisti: freqtrade/.venv/bin/python papers/77_youtube_classics/test.py"""
import os, numpy as np, pandas as pd
R = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "freqtrade/user_data/data/binance")
def rsi(x, n):
    d = x.diff(); u = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean(); v = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean(); return 100 - 100/(1 + u/v)
def ema(x, n): return x.ewm(span=n, adjust=False).mean()
def smma(x, n): return x.ewm(alpha=1/n, adjust=False).mean()
def macd200(d):
    c, l, h = d.close.values, d.low.values, d.high.values; m = ema(d.close, 12) - ema(d.close, 26); s = ema(m, 9); e200 = ema(d.close, 200).values
    up = ((m > s) & (m.shift() <= s.shift()) & (m < 0)).values; dn = ((m < s) & (m.shift() >= s.shift()) & (m > 0)).values
    lo14 = d.low.rolling(14).min().values; hi14 = d.high.rolling(14).max().values
    pos = np.zeros(len(c)); cur = 0; sl = tp = 0
    for i in range(200, len(c)):
        if cur == 1 and (l[i] <= sl or h[i] >= tp): cur = 0
        elif cur == -1 and (h[i] >= sl or l[i] <= tp): cur = 0
        if cur == 0:
            if up[i] and c[i] > e200[i]: sl = min(lo14[i], e200[i]); tp = c[i] + 1.5 * (c[i] - sl); cur = 1 if c[i] > sl else 0
            elif dn[i] and c[i] < e200[i]: sl = max(hi14[i], e200[i]); tp = c[i] - 1.5 * (sl - c[i]); cur = -1 if c[i] < sl else 0
        pos[i] = cur
    return pos
def stochrsi(d):
    r = rsi(d.close, 14); k = ((r - r.rolling(14).min()) / (r.rolling(14).max() - r.rolling(14).min())).rolling(3).mean() * 100; dd = k.rolling(3).mean()
    e = ema(d.close, 200); ent = (k > dd) & (k.shift() <= dd.shift()) & (k < 20) & (d.close > e); ex = (k > 80) | (d.close < e)
    ents = (k < dd) & (k.shift() >= dd.shift()) & (k > 80) & (d.close < e); exs = (k < 20) | (d.close > e)
    pos = np.zeros(len(d)); cur = 0
    for i in range(len(d)):
        if cur == 1 and ex.iloc[i]: cur = 0
        if cur == -1 and exs.iloc[i]: cur = 0
        if cur == 0: cur = 1 if ent.iloc[i] else (-1 if ents.iloc[i] else 0)
        pos[i] = cur
    return pos
def alligator(d):
    m = (d.high + d.low) / 2; jaw = smma(m, 13).shift(8); teeth = smma(m, 8).shift(5); lips = smma(m, 5).shift(3)
    return np.where((lips > teeth) & (teeth > jaw), 1, np.where((lips < teeth) & (teeth < jaw), -1, 0))
def heikin(d):
    hc = (d.open + d.high + d.low + d.close) / 4; ho = hc.copy(); ho.iloc[0] = (d.open.iloc[0] + d.close.iloc[0]) / 2
    hov = ho.to_numpy().copy(); hcv = hc.to_numpy()
    for i in range(1, len(d)): hov[i] = (hov[i-1] + hcv[i-1]) / 2
    g = pd.Series(hcv > hov, d.index); e = ema(d.close, 50)
    return np.where(g & g.shift(1, fill_value=False) & (d.close > e), 1, np.where(~g & ~g.shift(1, fill_value=True) & (d.close < e), -1, np.nan))
def ema921(d): return np.where(ema(d.close, 9) > ema(d.close, 21), 1, -1)
IND = {"MACD+200EMA": macd200, "StochRSI trendas": stochrsi, "Alligator": alligator, "Heikin Ashi+EMA50": heikin, "EMA 9/21": ema921}
def ret(d, s, mode):
    s = pd.Series(s, d.index).ffill().fillna(0); pos = s.clip(lower=0) if mode == "long" else s; fee = 0.001 if mode == "long" else 0.0005
    r = d.close.pct_change().fillna(0); p1 = pos.shift(1).fillna(0)
    return pd.Series((p1 * r - pos.diff().abs().fillna(0) * fee).values, d.date)
def st(x, a, b):
    x = x[(x.index >= pd.Timestamp(a, tz="UTC")) & (x.index < pd.Timestamp(b, tz="UTC"))]; e = (1 + x).cumprod(); y = (x.index[-1] - x.index[0]).days / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+6.1f}% kr {(e / e.cummax() - 1).min() * 100:4.0f}%"
PER = [("2018-06-01", "2022-01-01"), ("2022-01-01", "2027-01-01")]
ALTS = "XRP BNB SOL DOGE ADA TRX LINK AVAX LTC DOT".split()
print("periodai: 2018-06–21 | 2022–26")
for tf in ("1h", "4h", "1d"):
    data = {c: pd.read_feather(f"{R}/{c}_USDT-{tf}.feather") for c in ["BTC", "ETH"] + ALTS}
    for nm, f in IND.items():
        sig = {c: f(d) for c, d in data.items()}
        for mode in ("long", "ls"):
            be = pd.concat([ret(data[c], sig[c], mode) for c in ("BTC", "ETH")], axis=1, sort=True).fillna(0).mean(axis=1)
            al = pd.concat([ret(data[c], sig[c], mode) for c in ALTS], axis=1, sort=True).fillna(0).mean(axis=1)
            print(f"{tf} {nm:18s} {mode:4s}: BTC+ETH {' | '.join(st(be, a, b) for a, b in PER)} || alts10 {' | '.join(st(al, a, b) for a, b in PER)}", flush=True)
