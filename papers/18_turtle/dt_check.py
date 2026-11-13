"""Dual Thrust BTC+ETH patikra: parametrų jautrumas (dienos) ir 5m vykdymas (freqtrade 5m duomenys 2021-11 – 2026-11)."""
import os, numpy as np, pandas as pd
__file__ = os.path.abspath("test.py")
exec(open("test.py").read().split("rows = []")[0])
data = {s: load(s) for s in ["BTC", "ETH"]}
print("Jautrumas (dienos OHLC, 0,1 %): n × k -> 2018–21 | 2021–26")
for n in [2, 3, 4, 5, 6]:
    line = []
    for k in [0.5, 0.6, 0.7, 0.8, 0.9]:
        R = pd.concat([dual_thrust(d, n, k)[0] for d in data.values()], axis=1)["2018":].fillna(0).mean(axis=1)
        line.append(f"k{k}: {st(R, '2018-01-01', '2021-11-08')} | {st(R, '2021-11-08', '2026-11-08')}")
    print(f"n={n}: " + "  ".join(line))
# 5m vykdymas: pirmas 5m baras, kurio high > riba -> įėjimas max(open, riba); išėjimas dienos paskutinio 5m baro uždarymu
F = "../../freqtrade/user_data/data/binance/"
for fee in [0.001, 0.0015]:
    out = {}
    for s, d in data.items():
        m5 = pd.read_feather(f"{F}{s}_USDT-5m.feather").set_index("date"); m5.index = m5.index.tz_localize(None)
        n, k = 4, 0.7
        rng = pd.concat([d.h.rolling(n).max() - d.c.rolling(n).min(), d.c.rolling(n).max() - d.l.rolling(n).min()], axis=1).max(axis=1).shift(1)
        r = pd.Series(0.0, d.index)
        for day, g in m5.groupby(m5.index.floor("D")):
            if day not in d.index or np.isnan(rng.get(day, np.nan)): continue
            up = g.open.iloc[0] + k * rng[day]
            hit = g.high.values > up
            if not hit.any(): continue
            j = hit.argmax(); px = max(g.open.iloc[j], up)
            r[day] = g.close.iloc[-1] / px - 1 - 2 * fee
        out[s] = r
    R = pd.concat(out, axis=1)["2021-11-08":"2026-11-08"].fillna(0).mean(axis=1)
    y = (1 + R).groupby(R.index.year).prod() - 1
    Rd = pd.concat([dual_thrust(d, 4, 0.7)[0] for d in data.values()], axis=1)["2021-11-08":"2026-11-08"].fillna(0).mean(axis=1)
    print(f"5m vykdymas, mokestis {fee*100:.2f} %: {st(R, '2021-11-08', '2026-11-08')}, metai {dict((k_, round(v*100,1)) for k_, v in y.items())}; dienos OHLC: {st(Rd, '2021-11-08', '2026-11-08')}")
