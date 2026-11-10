"""Noise Breakout patobulinimų paieška. Renkamasi pagal 2021-03..2024-12, tikrinama 2025-01..2026-11.
Variantai (visi žinomi priedai, ne nauja strategija):
  mult  – ribų plotis × (platesnės ribos = mažiau klaidingų proveržių)
  trend – dienos trendo filtras: long tik kai vakar close > SMA(n), short tik kai žemiau (0 = išjungta)
  stop  – "paper": max(riba, VWAP); "vwap": tik VWAP; "band": tik riba
  step  – kas kiek min. tikrinama
"""
import sys, itertools, json
import numpy as np
import pandas as pd
from multiprocessing import Pool
from sim import load
from intraday import rth

FEE = 0.00003


def prep(ny, lookback=14, tf=5):
    days = sorted(ny.day.unique())
    by = {d: g for d, g in ny.groupby("day")}
    closes = pd.Series({d: by[d].close.iloc[-1] for d in days})
    out, hist, prev = [], [], None
    for d in days:
        g = by[d]
        full = g.tod.iloc[0] == 570
        if full and len(hist) >= lookback and prev is not None and len(g) >= int(0.9 * 390 / tf):
            sigma = pd.concat(hist[-lookback:], axis=1).mean(axis=1).reindex(g.tod.values).values
            tp = (g.high + g.low + g.close) / 3
            v = g.volume.replace(0, np.nan).fillna(1)
            out.append(dict(day=d, tod=g.tod.values, close=g.close.values, o=g.open.iloc[0], prev=prev,
                            sigma=sigma, vwap=((tp * v).cumsum() / v.cumsum()).values))
        if full:
            hist.append(pd.Series((g.close / g.open.iloc[0] - 1).abs().values, index=g.tod.values))
        prev = g.close.iloc[-1]
    return out, closes


def run_cfg(args):
    D, closes, mult, trend, stop, step, lo = args[:7]
    tf = args[7] if len(args) > 7 else 5
    sma = closes.rolling(trend).mean().shift(1) if trend else None
    pc = closes.shift(1)
    res = []
    for x in D:
        d = x["day"]
        allow_l = allow_s = True
        if trend:
            s = sma.get(d)
            if s is None or np.isnan(s):
                continue
            allow_l, allow_s = pc[d] > s, pc[d] < s
        if lo:
            allow_s = False
        U0, L0 = max(x["o"], x["prev"]), min(x["o"], x["prev"])
        pos, e = 0, 0.0
        n = len(x["close"])
        for j in range(n):
            t = x["tod"][j] + tf
            last = j == n - 1
            if not ((t % step == 0 and t >= 600) or last):
                continue
            s_ = x["sigma"][j]
            if np.isnan(s_):
                continue
            c, v = x["close"][j], x["vwap"][j]
            U, L = U0 * (1 + mult * s_), L0 * (1 - mult * s_)
            sl_l = {"paper": max(U, v), "vwap": v, "band": U}[stop]
            sl_s = {"paper": min(L, v), "vwap": v, "band": L}[stop]
            if pos == 1 and (c < sl_l or last):
                res.append((d, c / e - 1 - 2 * FEE)); pos = 0
            elif pos == -1 and (c > sl_s or last):
                res.append((d, -(c / e - 1) - 2 * FEE)); pos = 0
            if pos == 0 and not last:
                if c > U and allow_l:
                    pos, e = 1, c
                elif c < L and allow_s:
                    pos, e = -1, c
    t = pd.DataFrame(res, columns=["day", "ret"])
    t["day"] = pd.to_datetime(t.day)
    return dict(mult=mult, trend=trend, stop=stop, step=step, lo=lo, tr=st(t, "2021-03-01", "2025-01-01"),
                te=st(t, "2025-01-01", "2026-11-10"))


def st(t, a, b):
    t = t[(t.day >= a) & (t.day < b)]
    if len(t) < 30:
        return dict(n=len(t), cagr=0, dd=99, pf=0, mpos=0, win=0)
    yrs = (pd.Timestamp(b) - pd.Timestamp(a)).days / 365.25
    eq = (1 + t.ret).cumprod()
    m = t.groupby(t.day.dt.to_period("M")).ret.apply(lambda r: (1 + r).prod() - 1)
    g, l = t.ret[t.ret > 0].sum(), -t.ret[t.ret < 0].sum()
    return dict(n=len(t), cagr=round(100 * (eq.iloc[-1] ** (1 / yrs) - 1), 1), dd=round(100 * (1 - eq / eq.cummax()).max(), 1),
                pf=round(g / l, 2), mpos=round(100 * (m > 0).mean()), win=round(100 * (t.ret > 0).mean()))


if __name__ == "__main__":
    ny = rth(load(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "NAS100", "5min"))
    D, closes = prep(ny)
    grid = list(itertools.product([1.0, 1.25, 1.5], [0, 50, 200], ["paper", "vwap", "band"], [30, 60], [False, True]))
    with Pool(16) as p:
        R = p.map(run_cfg, [(D, closes, *g) for g in grid])
    json.dump(R, open("noise2_grid.json", "w"), default=float)
    R.sort(key=lambda r: -(r["tr"]["cagr"] / max(r["tr"]["dd"], 3)))
    base = next(r for r in R if r["mult"] == 1.0 and r["trend"] == 0 and r["stop"] == "paper" and r["step"] == 30 and not r["lo"])
    print("BAZĖ", base)
    for r in R[:15]:
        print(r)
