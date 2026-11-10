"""EI3v2 TradingView indikatoriaus (tradingview/EI3v2_tag_cofi_green.pine) kopija Python'e,
kad būtų galima testuoti ant indeksų (NAS100, SPX500, US30) 5m/15m duomenų (Dukascopy).

Naudojimas: python sim.py <data_dir>   (data_dir su <NAME>_<metai>.csv)
"""
import sys, itertools, json
from pathlib import Path
import numpy as np
import pandas as pd


# ---------- Pine ta.* atitikmenys ----------
def ema(s, n):
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def rma(s, n):
    return s.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def rsi(s, n):
    d = s.diff()
    up, dn = rma(d.clip(lower=0), n), rma((-d).clip(lower=0), n)
    return 100 - 100 / (1 + up / dn)


def wma(s, n):
    w = np.arange(1, n + 1)
    return s.rolling(n).apply(lambda x: np.dot(x, w) / w.sum(), raw=True)


def hma(s, n):
    return wma(2 * wma(s, n // 2) - wma(s, n), int(np.sqrt(n)))


def adx(df, n=14):
    up, dn = df.high.diff(), -df.low.diff()
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = pd.concat([df.high - df.low, (df.high - df.close.shift()).abs(), (df.low - df.close.shift()).abs()], axis=1).max(axis=1)
    atr = rma(tr, n)
    pdi = 100 * rma(pd.Series(pdm, df.index), n) / atr
    mdi = 100 * rma(pd.Series(mdm, df.index), n) / atr
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi)
    return rma(dx, n)


# ---------- duomenys ----------
def load(data_dir, name, tf):
    fs = sorted(Path(data_dir).glob(f"{name}_*.csv"))
    df = pd.concat(pd.read_csv(f, index_col=0, parse_dates=True) for f in fs)
    df = df[~df.index.duplicated()].sort_index()[["open", "high", "low", "close", "volume"]]
    if tf != "5min":
        df = df.resample(tf, label="left", closed="left").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
    return df


def indicators(df, bars_per_day):
    c = df.close
    x = pd.DataFrame(index=df.index)
    x["emaBuy"], x["emaSell"], x["hma50"] = ema(c, 12), ema(c, 22), hma(c, 50)
    x["ewo"] = (ema(c, 50) - ema(c, 200)) / c * 100
    x["rsi14"], x["rsi4"], x["rsi20"] = rsi(c, 14), rsi(c, 4), rsi(c, 20)
    x["ema14"], x["ema8"] = ema(c, 14), ema(c, 8)
    ll, hh = df.low.rolling(5).min(), df.high.rolling(5).max()
    x["fastk"] = 100 * (c - ll) / (hh - ll)
    x["fastd"] = x.fastk.rolling(3).mean()
    x["adx"] = adx(df)
    rng = (df.high - df.low) / c * 100
    x["medRange"] = rng.rolling(1000).median()
    vol = df.volume
    x["noVol"] = vol.cumsum() == 0
    vs, vl = vol.rolling(4).mean(), vol.rolling(48).mean().shift(bars_per_day)
    x["pnd"] = (~x.noVol) & (vl > 0) & (vs / vl > 5)
    # 1h RSI(8) paties grafiko, tik užsidariusi valanda
    h = c.resample("1h", label="left", closed="left").last().dropna()
    r8 = rsi(h, 8).shift(1)
    x["fltRsi"] = r8.reindex(df.index.floor("1h")).values
    return x


def signals(df, x, k, flt=True):
    sc = lambda off: 1 + (off - 1) * k
    c, o = df.close, df.open
    volOk = x.noVol | (df.volume > 0)
    lambo2 = (c < x.ema14 * sc(0.981)) & (x.rsi4 < 44) & (x.rsi14 < 39)
    buy1 = (x.rsi4 < 35) & (c < x.emaBuy * sc(0.987)) & (x.ewo > 3.001 * k) & (x.rsi14 < 58) & volOk & (c < x.emaSell * sc(1.014))
    buy2 = (x.rsi4 < 35) & (c < x.emaBuy * sc(0.987)) & (x.ewo < -10.289 * k) & volOk & (c < x.emaSell * sc(1.014))
    kUp = (x.fastk > x.fastd) & (x.fastk.shift() <= x.fastd.shift())
    cofi = (o < x.ema8 * sc(0.98)) & kUp & (x.fastk < 22) & (x.fastd < 20) & (x.adx > 20) & (x.ewo > 4.179 * k)
    buy = (lambo2 | buy1 | buy2 | cofi) & ~x.pnd
    if flt:
        buy &= ~(x.fltRsi < 35)
    sell = volOk & (x.rsi4 > x.rsi20) & (((c > x.hma50) & (c > x.emaSell * sc(1.01)) & (x.rsi14 > 50)) |
                                         ((c < x.hma50) & (c > x.emaSell * sc(1.014))))
    return buy.fillna(False).values, sell.fillna(False).values


def simulate(df, buy, sell, k, fee=0.0001, trail_off=1.2, trail_dist=0.1, sig_min=1.0, unclog=-4.0,
             unclog_days=4, cooldown=5, sl=None, session=None, eod=None):
    """Kaip Pine: įėjimas kitos žvakės open, trailing/signalas/unclog. sl: stop-loss % (×k) arba None."""
    O, H, L, C = (df[c].values for c in ("open", "high", "low", "close"))
    T = df.index.values.astype("datetime64[m]").astype(np.int64)
    ok_sess = np.ones(len(df), bool) if session is None else session
    K = np.broadcast_to(np.asarray(k, float), (len(df),))
    pft = lambda p, e: (p * (1 - fee) - e * (1 + fee)) / (e * (1 + fee))
    trades = []  # (entry_time, exit_time, return)
    inpos = pending = False
    last_exit = -10 ** 9
    for i in range(len(df)):
        if pending:
            pending, inpos = False, True
            e, et, ei, mx = O[i], T[i], i, O[i]
            kk = K[i]
            to, td, sm, uc = trail_off * kk / 100, trail_dist * kk / 100, sig_min * kk / 100, unclog * kk / 100
            slp = None if sl is None else sl * kk / 100
            tp = e * (1 + fee) * (1 + to) / (1 - fee)
            stop_loss = None if slp is None else e * (1 - slp)
        if inpos:
            ex = None
            if mx >= tp and O[i] <= mx * (1 - td):
                ex = O[i]
            if ex is None and stop_loss is not None and L[i] <= stop_loss:
                ex = min(O[i], stop_loss)
            if ex is None:
                mx = max(mx, H[i])
                if mx >= tp and L[i] <= mx * (1 - td):
                    ex = mx * (1 - td)
            if ex is None and sell[i] and pft(C[i], e) >= sm:
                ex = C[i]
            if ex is None and pft(C[i], e) < uc and T[i] - et >= unclog_days * 1440:
                ex = C[i]
            if ex is None and eod is not None and eod[i]:
                ex = C[i]
            if ex is not None:
                trades.append((et, T[i], pft(ex, e)))
                inpos, last_exit = False, i
        if buy[i] and ok_sess[i] and not inpos and not pending and i - last_exit > cooldown:
            pending = True
    return pd.DataFrame(trades, columns=["entry", "exit", "ret"])


def stats(tr, start, end):
    t = tr[(tr.entry >= start) & (tr.entry < end)]
    years = (end - start) / (365.25 * 1440)
    if len(t) == 0:
        return dict(n=0, win=0, cagr=0, dd=0, pf=0, per_week=0)
    eq = (1 + t.ret).cumprod()
    dd = (1 - eq / eq.cummax()).max()
    g, l = t.ret[t.ret > 0].sum(), -t.ret[t.ret < 0].sum()
    return dict(n=len(t), win=round(100 * (t.ret > 0).mean(), 1), cagr=round(100 * (eq.iloc[-1] ** (1 / years) - 1), 1),
                dd=round(100 * dd, 1), pf=round(g / l, 2) if l else 99, per_week=round(len(t) / years / 52, 1),
                avg=round(100 * t.ret.mean(), 3))


def sessions(df, tf_min):
    ny = df.index.tz_convert("America/New_York")
    mins = ny.hour * 60 + ny.minute
    rth = (mins >= 570) & (mins < 960)
    eod = mins == 960 - tf_min
    return np.asarray(rth), np.asarray(eod)
