"""Noise Breakout bet kokiai rinkai/sesijai. python noise3.py <data> <NAME> <tz> <HH:MM-HH:MM>"""
import sys, numpy as np, pandas as pd
from sim import load
FEE = 0.00003
def sess(df, tz, a, b):
    x = df.copy(); x.index = x.index.tz_convert(tz)
    m = x.index.hour * 60 + x.index.minute
    x = x[(m >= a) & (m < b)].copy(); x["day"] = x.index.date; x["tod"] = x.index.hour * 60 + x.index.minute
    return x
def run(x, a, b, step=60, lookback=14, tf=5, lo=False):
    by = {d: g for d, g in x.groupby("day")}; hist, prev, res = [], None, []
    for d in sorted(by):
        g = by[d]; full = g.tod.iloc[0] == a
        if full and len(hist) >= lookback and prev is not None and len(g) >= 0.9 * (b - a) / tf:
            sig = pd.concat(hist[-lookback:], axis=1).mean(axis=1).reindex(g.tod.values).values
            tp = (g.high + g.low + g.close) / 3; v = g.volume.replace(0, np.nan).fillna(1)
            vw = ((tp * v).cumsum() / v.cumsum()).values; C = g.close.values; T = g.tod.values
            U0, L0 = max(g.open.iloc[0], prev), min(g.open.iloc[0], prev); pos = 0
            for j in range(len(g)):
                t = T[j] + tf; last = j == len(g) - 1
                if not (((t - a) % step == 0 and t >= a + 30) or last) or np.isnan(sig[j]): continue
                c, U, L = C[j], U0 * (1 + sig[j]), L0 * (1 - sig[j])
                if pos == 1 and (c < max(U, vw[j]) or last): res.append((d, c / e - 1 - 2 * FEE)); pos = 0
                elif pos == -1 and (c > min(L, vw[j]) or last): res.append((d, -(c / e - 1) - 2 * FEE)); pos = 0
                if pos == 0 and not last:
                    if c > U: pos, e = 1, c
                    elif c < L and not lo: pos, e = -1, c
        if full: hist.append(pd.Series((g.close / g.open.iloc[0] - 1).abs().values, index=g.tod.values))
        prev = g.close.iloc[-1]
    t = pd.DataFrame(res, columns=["day", "ret"]); t["day"] = pd.to_datetime(t.day); return t
def st(t, a, b):
    t = t[(t.day >= a) & (t.day < b)]
    if len(t) < 20: return {}
    y = (pd.Timestamp(b) - pd.Timestamp(a)).days / 365.25; eq = (1 + t.ret).cumprod()
    g, l = t.ret[t.ret > 0].sum(), -t.ret[t.ret < 0].sum()
    return dict(n=len(t), cagr=round(100 * (eq.iloc[-1] ** (1 / y) - 1), 1), dd=round(100 * (1 - eq / eq.cummax()).max(), 1), pf=round(g / l, 2))
if __name__ == "__main__":
    D, name, tz, s = sys.argv[1:5]
    a, b = [int(h) * 60 + int(m) for h, m in (p.split(":") for p in s.split("-"))]
    x = sess(load(D, name, "5min"), tz, a, b)
    c = x.groupby("day").close.last(); yrs = (c.index[-1] - c.index[0]).days / 365.25
    print(name, s, tz, "| laikyti %.1f%%/m" % (100 * ((c.iloc[-1] / c.iloc[0]) ** (1 / yrs) - 1)))
    for step in (30, 60):
        for lo in (False, True):
            t = run(x, a, b, step, lo=lo)
            print(f"  kas {step} min {'tik long' if lo else 'long+short'}: 2021-24", st(t, "2021-03-01", "2025-01-01"), "| 2025-26", st(t, "2025-01-01", "2026-11-10"))
