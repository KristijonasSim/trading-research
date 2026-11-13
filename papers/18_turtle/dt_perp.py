"""Dual Thrust ant Binance perp BTC/ETH (2019-09 – 2026-11): long ir long+short, mokestis 0,05 % / 0,02 %, funding 08 ir 16 UTC
(pozicija laikoma nuo pramušimo iki 00 UTC; funding skaičiuojamas, jei įėjimas prieš 08 ar 16 val. – supaprastinta: 2 iš 3 mokėjimų × tikimybė)."""
import numpy as np, pandas as pd
D = "../data/"
def load(s):
    d = pd.read_csv(f"{D}perp_1d/{s}USDT.csv"); d.index = pd.to_datetime(d.t, unit="ms")
    f = pd.read_csv(f"{D}funding/{s}USDT.csv"); f.index = pd.to_datetime(f.t, unit="ms")
    fd = f.rate.groupby(f.index.floor("D")).sum().reindex(d.index).fillna(0)
    return d[["o", "h", "l", "c"]], fd
def dt(d, fd, n, k, fee, short):
    rng = pd.concat([d.h.rolling(n).max() - d.c.rolling(n).min(), d.c.rolling(n).max() - d.l.rolling(n).min()], axis=1).max(axis=1).shift(1)
    up = d.o + k * rng; dn = d.o - k * rng
    L = d.h > up; S = (d.l < dn) & short
    rl = np.where(L, d.c / np.maximum(d.o, up) - 1 - 2 * fee - fd * 2 / 3, 0.0)
    rs = np.where(S, 1 - d.c / np.minimum(d.o, dn) - 2 * fee + fd * 2 / 3, 0.0)
    both = L & S   # abu pramušimai tą pačią dieną: nežinoma tvarka -> konservatyviai nuostolis abiejose
    r = np.where(both, np.minimum(rl, 0) + np.minimum(rs, 0), rl + rs)
    return pd.Series(r, d.index).fillna(0)
def st(r, a, b):
    r = r[a:b]; eq = (1 + r).cumprod(); y = (r.index[-1] - r.index[0]).days / 365.25
    return f"{(eq.iloc[-1] ** (1 / y) - 1) * 100:+.1f} ({(eq / eq.cummax() - 1).min() * 100:.0f})"
data = {s: load(s) for s in ["BTC", "ETH"]}
for short in [False, True]:
    for fee in [0.0005, 0.0002]:
        for n, k in [(4, 0.7), (4, 0.5), (5, 0.7)]:
            R = pd.concat([dt(d, fd, n, k, fee, short) for d, fd in data.values()], axis=1).fillna(0).mean(axis=1)
            y = (1 + R["2020":]).groupby(R["2020":].index.year).prod() - 1
            print(f"{'long+short' if short else 'long'} fee {fee*100:.2f} n{n} k{k}: 2020–21-11 {st(R, '2020-01-01', '2021-11-08')} | 2021-11–26 {st(R, '2021-11-08', '2026-11-08')} | {dict((a, round(b*100)) for a, b in y.items())}", flush=True)
