"""53: MVRV (Mahmudov, Puell 2018) – BTC/ETH ciklo laikas pagal rinkos/realizuotos kapitalizacijos santykį.
Duomenys: Coin Metrics community API (CapMVRVCur, PriceUSD), 1d. Signalas dienos t pabaigoje, prekyba t+1 uždarymu
(1 d. vėlavimas, nes CM duomenys skelbiami po dienos pabaigos). Mokestis 0,1 % už sandorį.
Paskelbta 2018-10 -> nematytas laikotarpis 2018-10 – 2026-11. Paleisti: python3 papers/53_mvrv/test.py"""
import json, os, itertools
import numpy as np, pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); FEE = 0.001
d = pd.DataFrame(json.load(open(f"{D}/data/cm.json"))["data"])
d["time"] = pd.to_datetime(d.time).dt.tz_localize(None)
for c in ("CapMVRVCur", "PriceUSD"): d[c] = d[c].astype(float)

def bt(px, pos):
    pos = pos.shift(1).fillna(0)                       # 1 d. vėlavimas
    r = px.pct_change().fillna(0) * pos - pos.diff().abs().fillna(0) * FEE
    return (1 + r).cumprod()
def st(e, a, b):
    e = e[(e.index >= a) & (e.index < b)]; e = e / e.iloc[0]
    y = (e.index[-1] - e.index[0]).days / 365.25
    yr = e.resample("YE").last(); yr = pd.concat([pd.Series([1.0], [e.index[0]]), yr]).pct_change().dropna()
    return round(((e.iloc[-1]) ** (1 / y) - 1) * 100, 1), round((e / e.cummax() - 1).min() * 100), {k.year: round(v * 100) for k, v in yr.items()}

out = []
for asset in ("btc", "eth"):
    x = d[d.asset == asset].set_index("time"); px, m = x.PriceUSD, x.CapMVRVCur
    tr = lambda a: int(((a.diff().abs()) > 0).sum())
    print(f"\n== {asset.upper()} ==  laikyti 2018-10–2026-11: {st(px/px.iloc[0], '2018-10-01', '2027-01-01')}  2021-11–2026-11: {st(px/px.iloc[0], '2021-11-08', '2027-01-01')[:2]}")
    # A) ciklas: pirkti kai MVRV < lo, parduoti kai > hi (histerezė)
    for lo, hi in itertools.product((1.0, 1.5, 2.0), (2.5, 3.0, 3.5)):
        p = pd.Series(np.nan, m.index); p[m < lo] = 1; p[m > hi] = 0; p = p.ffill().fillna(0)
        e = bt(px, p); r = (st(e, "2018-10-01", "2027-01-01"), st(e, "2021-11-08", "2027-01-01")[:2])
        print(f"A ciklas lo={lo} hi={hi}: 2018-10–26 {r[0][0]:+6.1f}%/m. kr {r[0][1]}% | 2021-11–26 {r[1][0]:+6.1f}% kr {r[1][1]}% | sandorių {tr(p)} | {r[0][2]}")
    # B) MVRV trendas: laikyti kai MVRV > jo N d. vidurkis
    for n in (50, 100, 200, 365):
        p = (m > m.rolling(n).mean()).astype(float)
        e = bt(px, p); r = (st(e, "2018-10-01", "2027-01-01"), st(e, "2021-11-08", "2027-01-01")[:2])
        print(f"B MVRV>{n}d vid.: 2018-10–26 {r[0][0]:+6.1f}%/m. kr {r[0][1]}% | 2021-11–26 {r[1][0]:+6.1f}% kr {r[1][1]}% | sandorių {tr(p)} | {r[0][2]}")
    # C) palyginimui – kainos SMA tuo pačiu periodu (MVRV = kaina / realizuota kaina, todėl artimas)
    for n in (100, 200):
        p = (px > px.rolling(n).mean()).astype(float)
        e = bt(px, p); r = (st(e, "2018-10-01", "2027-01-01"), st(e, "2021-11-08", "2027-01-01")[:2])
        print(f"C kaina>{n}d SMA: 2018-10–26 {r[0][0]:+6.1f}%/m. kr {r[0][1]}% | 2021-11–26 {r[1][0]:+6.1f}% kr {r[1][1]}% | sandorių {tr(p)}")
