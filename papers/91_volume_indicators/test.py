"""91: Apimties indikatorių klasika: Granville OBV (OBV > jo 20 EMA), Chaikin Money Flow (CMF20 > 0,05 / < −0,05), MFI(14) atšokimas (< 20 pirkti, > 80 parduoti),
slenkantis VWAP trendas (kaina > 20 barų VWAP). BTC+ETH ir alts10, 4h ir 1d, long-only spot 0,1 % ir long+short perp 0,05 %.
Signalas uždarymu, pozicija nuo kito baro. Paleisti: freqtrade/.venv/bin/python papers/91_volume_indicators/test.py"""
import os, numpy as np, pandas as pd
R = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "freqtrade/user_data/data/binance")
def obv(d):
    o = (np.sign(d.close.diff()).fillna(0) * d.volume).cumsum(); return np.where(o > o.ewm(span=20, adjust=False).mean(), 1, -1)
def cmf(d):
    mfm = ((d.close - d.low) - (d.high - d.close)) / (d.high - d.low).replace(0, np.nan); c = (mfm * d.volume).rolling(20).sum() / d.volume.rolling(20).sum()
    return np.where(c > 0.05, 1, np.where(c < -0.05, -1, np.nan))
def mfi(d):
    tp = (d.high + d.low + d.close) / 3; mf = tp * d.volume; up = mf.where(tp > tp.shift(), 0).rolling(14).sum(); dn = mf.where(tp < tp.shift(), 0).rolling(14).sum()
    m = 100 - 100 / (1 + up / dn); return np.where(m < 20, 1, np.where(m > 80, -1, np.nan))
def vwap(d):
    tp = (d.high + d.low + d.close) / 3; v = (tp * d.volume).rolling(20).sum() / d.volume.rolling(20).sum(); return np.where(d.close > v, 1, -1)
IND = {"OBV > EMA20": obv, "Chaikin MF": cmf, "MFI atšokimas": mfi, "VWAP20 trendas": vwap}
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
for tf in ("4h", "1d"):
    data = {c: pd.read_feather(f"{R}/{c}_USDT-{tf}.feather") for c in ["BTC", "ETH"] + ALTS}
    for nm, f in IND.items():
        sig = {c: f(d) for c, d in data.items()}
        for mode in ("long", "ls"):
            be = pd.concat([ret(data[c], sig[c], mode) for c in ("BTC", "ETH")], axis=1, sort=True).fillna(0).mean(axis=1)
            al = pd.concat([ret(data[c], sig[c], mode) for c in ALTS], axis=1, sort=True).fillna(0).mean(axis=1)
            print(f"{tf} {nm:15s} {mode:4s}: BTC+ETH {' | '.join(st(be, a, b) for a, b in PER)} || alts10 {' | '.join(st(al, a, b) for a, b in PER)}", flush=True)
