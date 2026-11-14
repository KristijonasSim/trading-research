"""94 patikra: SimpleBollinger 1d alts10 – BB ilgis/plotis, metai, be vienos monetos, 2x mokestis, išėjimas ties vidurine vs apatine."""
import os, numpy as np, pandas as pd
R = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "freqtrade/user_data/data/binance")
ALTS = "XRP BNB SOL DOGE ADA TRX LINK AVAX LTC DOT".split()
data = {c: pd.read_feather(f"{R}/{c}_USDT-1d.feather") for c in ALTS + ["BTC", "ETH"]}
def sb(d, n, k, exit_mid=True):
    m = d.close.rolling(n).mean(); sd = d.close.rolling(n).std(); up = m + k * sd; ex = d.close < (m if exit_mid else m - k * sd)
    pos = np.zeros(len(d)); cur = 0; e = (d.close > up).values; x = ex.values
    for i in range(len(d)):
        if cur and x[i]: cur = 0
        if not cur and e[i]: cur = 1
        pos[i] = cur
    return pos
def ret(d, pos, fee):
    pos = pd.Series(pos, d.index); r = d.close.pct_change().fillna(0); return pd.Series((pos.shift(1).fillna(0) * r - pos.diff().abs().fillna(0) * fee).values, d.date)
def cg(x, a, b):
    x = x[(x.index >= pd.Timestamp(a, tz="UTC")) & (x.index < pd.Timestamp(b, tz="UTC"))]; e = (1 + x).cumprod(); y = (x.index[-1] - x.index[0]).days / 365.25
    return (e.iloc[-1] ** (1 / y) - 1) * 100, (e / e.cummax() - 1).min() * 100
def port(coins, n=20, k=2.0, fee=0.001, mid=True):
    return pd.concat([ret(data[c], sb(data[c], n, k, mid), fee) for c in coins], axis=1, sort=True).fillna(0).mean(axis=1)
print("BB(n,k) 1d alts10, long: 2018-06–21 | 2022–26 (CAGR / kritimas)")
for n in (10, 20, 30, 50):
    print(f"  n={n:2d} " + "  ".join(f"k={k}: {cg(port(ALTS, n, k), '2018-06-01', '2022-01-01')[0]:+6.1f}/{cg(port(ALTS, n, k), '2018-06-01', '2022-01-01')[1]:.0f} | {cg(port(ALTS, n, k), '2022-01-01', '2027-01-01')[0]:+5.1f}/{cg(port(ALTS, n, k), '2022-01-01', '2027-01-01')[1]:.0f}" for k in (1.5, 2.0, 2.5)))
b = port(ALTS); print("mokestis 0,2 %:", [round(v, 1) for v in cg(port(ALTS, fee=0.002), '2022-01-01', '2027-01-01')], "| išėjimas ties apatine:", [round(v, 1) for v in cg(port(ALTS, mid=False), '2022-01-01', '2027-01-01')])
yr = (1 + b).groupby(b.index.year).prod() - 1; h = pd.concat([data[c].set_index("date").close.pct_change() for c in ALTS], axis=1).fillna(0).mean(axis=1); hy = (1 + h).groupby(h.index.year).prod() - 1
print("metai (strategija / laikymas):", {k: f"{v*100:+.0f}/{hy[k]*100:+.0f}" for k, v in yr.items()})
print("be vienos monetos 2022–26:", {c: round(cg(port([x for x in ALTS if x != c]), '2022-01-01', '2027-01-01')[0], 1) for c in ALTS})
print("kiekviena moneta atskirai 2022–26:", {c: round(cg(port([c]), '2022-01-01', '2027-01-01')[0], 1) for c in ALTS})
