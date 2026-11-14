"""73: TradingView populiarieji II: Range Filter (DonovanWall, per=100, mult=3), HalfTrend (everget, amp=2), Coral Trend (LazyBear, sm=21, cd=0,4),
Pivot Reversal (TV vidinė strategija, 4/2), Donchian Trend Ribbon (dc=20). Kryptis long-only (spot 0,1 %) ir long+short (perp 0,05 %).
Signalas bar uždarymu, pozicija nuo kito baro. BTC, ETH ir alts10 (lygiais svoriais), 4h ir 1d, Binance 2018–2026.
Paleisti: freqtrade/.venv/bin/python papers/73_tv_trend2/test.py"""
import os, numpy as np, pandas as pd
R = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "freqtrade/user_data/data/binance")
def atr(d, n): tr = pd.concat([d.high - d.low, (d.high - d.close.shift()).abs(), (d.low - d.close.shift()).abs()], axis=1).max(axis=1); return tr.ewm(alpha=1/n, adjust=False).mean()
def range_filter(d, per=100, mult=3.0):
    c = d.close.values; ar = pd.Series(np.abs(np.diff(c, prepend=c[0]))).ewm(span=per, adjust=False).mean()
    sr = (ar.ewm(span=per * 2 - 1, adjust=False).mean() * mult).values; f = np.zeros(len(c)); f[0] = c[0]
    for i in range(1, len(c)):
        f[i] = max(f[i-1], c[i] - sr[i]) if c[i] > f[i-1] else min(f[i-1], c[i] + sr[i])
    up = pd.Series(np.sign(np.diff(f, prepend=f[0]))).replace(0, np.nan).ffill().fillna(0).values
    return np.where((c > f) & (up > 0), 1, np.where((c < f) & (up < 0), -1, np.nan))
def halftrend(d, amp=2, dev=2):
    h, l, c = d.high.values, d.low.values, d.close.values; n = len(c)
    hma = pd.Series(h).rolling(amp).mean().values; lma = pd.Series(l).rolling(amp).mean().values
    hh = pd.Series(h).rolling(amp).max().values; ll = pd.Series(l).rolling(amp).min().values
    trend = 0; maxl = l[0]; minh = h[0]; out = np.zeros(n)
    for i in range(amp, n):
        if trend == 0:
            maxl = max(ll[i], maxl)
            if hma[i] < maxl and c[i] < l[i-1]: trend = 1; minh = hh[i]
        else:
            minh = min(hh[i], minh)
            if lma[i] > minh and c[i] > h[i-1]: trend = 0; maxl = ll[i]
        out[i] = 1 if trend == 0 else -1
    return out
def coral(d, sm=21, cd=0.4):
    c = d.close.values; di = (sm - 1) / 2 + 1; c1 = 2 / (di + 1); c2 = 1 - c1; c3 = 3 * (cd * cd + cd ** 3); c4 = -3 * (2 * cd * cd + cd + cd ** 3); c5 = 3 * cd + 1 + cd ** 3 + 3 * cd * cd
    i1 = i2 = i3 = i4 = i5 = i6 = c[0]; bf = np.zeros(len(c))
    for k in range(len(c)):
        i1 = c1 * c[k] + c2 * i1; i2 = c1 * i1 + c2 * i2; i3 = c1 * i2 + c2 * i3; i4 = c1 * i3 + c2 * i4; i5 = c1 * i4 + c2 * i5; i6 = c1 * i5 + c2 * i6
        bf[k] = -cd ** 3 * i6 + c3 * i5 + c4 * i4 + c5 * i3
    return np.sign(np.diff(bf, prepend=bf[0]))
def pivot_rev(d, L=4, Rr=2):
    h, l, c = d.high, d.low, d.close
    ph = h.where((h.shift(Rr) == h.rolling(L + Rr + 1).max().shift(0)) & False)  # placeholder
    # pivot high patvirtinamas po Rr barų: h[i-Rr] yra max per [i-Rr-L, i]
    ph = h.shift(Rr).where(h.shift(Rr) == h.rolling(L + Rr + 1).max()).ffill()
    pl = l.shift(Rr).where(l.shift(Rr) == l.rolling(L + Rr + 1).min()).ffill()
    return np.where(h > ph.shift(), 1, np.where(l < pl.shift(), -1, np.nan))
def donchian_ribbon(d, n=20):
    c = d.close; up = c > d.high.rolling(n).max().shift(); dn = c < d.low.rolling(n).min().shift()
    return np.where(up, 1, np.where(dn, -1, np.nan))
IND = {"Range Filter": range_filter, "HalfTrend": halftrend, "Coral Trend": coral, "Pivot Reversal": pivot_rev, "Donchian Ribbon": donchian_ribbon}
def ret(d, s, mode):
    s = pd.Series(s, d.index).ffill().fillna(0)
    pos = s.clip(lower=0) if mode == "long" else s
    fee = 0.001 if mode == "long" else 0.0005
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
    hold = {c: pd.Series(d.close.pct_change().fillna(0).values, d.date) for c, d in data.items()}
    bh = (pd.concat([hold["BTC"], hold["ETH"]], axis=1).fillna(0).mean(axis=1)); ah = pd.concat([hold[c] for c in ALTS], axis=1).fillna(0).mean(axis=1)
    print(f"\n{tf} laikyti: BTC+ETH {' | '.join(st(bh, a, b) for a, b in PER)} || alts10 {' | '.join(st(ah, a, b) for a, b in PER)}")
    for nm, f in IND.items():
        sig = {c: f(d) for c, d in data.items()}
        for mode in ("long", "ls"):
            be = pd.concat([ret(data[c], sig[c], mode) for c in ("BTC", "ETH")], axis=1).fillna(0).mean(axis=1)
            al = pd.concat([ret(data[c], sig[c], mode) for c in ALTS], axis=1).fillna(0).mean(axis=1)
            print(f"{tf} {nm:16s} {mode:4s}: BTC+ETH {' | '.join(st(be, a, b) for a, b in PER)} || alts10 {' | '.join(st(al, a, b) for a, b in PER)}", flush=True)
