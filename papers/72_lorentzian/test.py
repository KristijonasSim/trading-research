"""72: TradingView „Machine Learning: Lorentzian Classification“ (jdehorty, 2022–23) – kNN su Lorentzo atstumu.
Požymiai (numatytieji): RSI(14), WaveTrend(10,11), CCI(20), ADX(20), RSI(9), normalizuoti į 0..1 (slenkantis min/max, be ateities).
Etiketė: ar kaina po 4 žvakių aukščiau (+1) ar žemiau (−1). Mokymas bare i naudoja tik barus j ≤ i−4 (etiketė jau žinoma), paskutinius 2000, kas 4-tą (kaip originale).
Prognozė = 8 artimiausių kaimynų etikečių suma; long kai > 0, short kai < 0 (perp), laikoma 4 žvakes (originalo „strict“ išėjimas), signalai kartojasi -> laikoma toliau.
Filtrai kaip originale: volatilumo (ATR1 > ATR10) ir režimo (KAMA nuolydis > −0,1 apytiksliai). Mokestis 0,05 %/pusė. Signalas bar uždarymu, vykdymas kito atidarymu ≈ uždarymu.
Paleisti: freqtrade/.venv/bin/python papers/72_lorentzian/test.py"""
import os, numpy as np, pandas as pd
R = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "freqtrade/user_data/data/binance")
def rsi(x, n):
    d = x.diff(); u = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean(); v = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean(); return 100 - 100/(1 + u/v)
def feats(d):
    c, h, l = d.close, d.high, d.low; hlc3 = (h + l + c) / 3
    esa = hlc3.ewm(span=10, adjust=False).mean(); de = (hlc3 - esa).abs().ewm(span=10, adjust=False).mean(); ci = (hlc3 - esa) / (0.015 * de)
    wt = ci.ewm(span=11, adjust=False).mean()
    tp = hlc3; cci = (tp - tp.rolling(20).mean()) / (0.015 * tp.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True))
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    up, dn = h.diff(), -l.diff(); pdm = ((up > dn) & (up > 0)) * up; ndm = ((dn > up) & (dn > 0)) * dn
    atr = tr.ewm(alpha=1/20, adjust=False).mean(); pdi = 100 * pdm.ewm(alpha=1/20, adjust=False).mean() / atr; ndi = 100 * ndm.ewm(alpha=1/20, adjust=False).mean() / atr
    adx = (100 * (pdi - ndi).abs() / (pdi + ndi)).ewm(alpha=1/20, adjust=False).mean()
    F = pd.concat([rsi(c, 14), wt, cci, adx, rsi(c, 9)], axis=1)
    lo, hi = F.rolling(500, min_periods=100).min(), F.rolling(500, min_periods=100).max()
    Fn = (F - lo) / (hi - lo)
    vol_ok = tr.rolling(1).mean() > tr.rolling(10).mean()
    reg = c.ewm(span=20, adjust=False).mean(); slope = reg.pct_change(5) * 100
    return Fn.values, vol_ok.values, (slope > -0.1).values
def run(d, k=8, H=4, fee=0.0005, filt=True):
    X, vok, rok = feats(d); c = d.close.values; n = len(c)
    lab = np.sign(np.r_[c[H:] - c[:-H], np.zeros(H)])
    sig = np.zeros(n)
    for i in range(700, n):
        js = np.arange(max(100, i - H - 2000), i - H + 1)[::-1][::4]
        Xj = X[js]; ok = ~np.isnan(Xj).any(axis=1) & ~np.isnan(X[i]).any()
        if ok.sum() < k: continue
        dist = np.log1p(np.abs(Xj[ok] - X[i])).sum(axis=1); nn = np.argpartition(dist, k)[:k]
        p = lab[js[ok][nn]].sum()
        if filt and not vok[i]: p = 0
        if filt and p > 0 and not rok[i]: p = 0
        sig[i] = np.sign(p)
    pos = np.zeros(n); hold = 0; cur = 0
    for i in range(n):
        if sig[i] != 0 and sig[i] != cur: cur = sig[i]; hold = H
        elif sig[i] == cur and cur != 0: hold = H
        elif hold > 0: hold -= 1
        if hold == 0: cur = 0
        pos[i] = cur
    r = np.r_[0, c[1:] / c[:-1] - 1]; p1 = np.r_[0, pos[:-1]]
    x = p1 * r - np.abs(np.diff(np.r_[0, pos])) * fee
    return pd.Series(x, d.date), pos
def st(x, a, b):
    x = x[(x.index >= pd.Timestamp(a, tz="UTC")) & (x.index < pd.Timestamp(b, tz="UTC"))]; e = (1 + x).cumprod(); y = (x.index[-1] - x.index[0]).days / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+6.1f}% kr {(e / e.cummax() - 1).min() * 100:4.0f}%"
PER = [("2018-06-01", "2022-01-01"), ("2022-01-01", "2027-01-01")]
print("periodai: 2018-06–21 | 2022–26 (long+short perp)")
for tf in ("4h", "1d"):
    for c in ("BTC", "ETH", "SOL", "XRP"):
        d = pd.read_feather(f"{R}/{c}_USDT-{tf}.feather")
        for filt in (True, False):
            x, pos = run(d, filt=filt); lo = pd.Series(np.maximum(pos, 0))
            hold = pd.Series(np.r_[0, d.close.values[1:] / d.close.values[:-1] - 1], d.date)
            print(f"{tf} {c} filtrai={'taip' if filt else 'ne  '}: {' | '.join(st(x, a, b) for a, b in PER)} | laikyti {' | '.join(st(hold, a, b) for a, b in PER)} | rinkoje {np.abs(pos).mean()*100:.0f}%", flush=True)
