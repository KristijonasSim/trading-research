"""Dvi paskelbtos dienos prekybos strategijos indeksams, 5m žvakės, tik JAV prekybos valandos (9:30–16:00 NY).

1) ORB 5m: Zarattini & Aziz (2023) "Can Day Trading Really Be Profitable?" (SSRN 4416622).
   Pirma 5m žvakė žalia -> long nuo 9:35 open, raudona -> short. Stop: pirmos žvakės low/high.
   TP: 10R. Kitaip uždaroma dienos pabaigoje.
2) Noise area: Zarattini, Aziz & Barbon (2024) "Beat the Market: An Effective Intraday Momentum
   Strategy for SPY" (SSRN 4824172). Ribos = max/min(open, vakar close) * (1 ± vid. 14 d. judėjimas
   tuo pačiu dienos laiku). Tikrinama kas 30 min.: virš viršutinės -> long, žemiau apatinės -> short.
   Stop: riba arba VWAP (kas arčiau kainos), tikrinamas kas 30 min. Uždaroma dienos pabaigoje.

Dydis: 1x (visas kapitalas, be sverto). Mokestis+spread: fee į vieną pusę.
"""
import sys
import numpy as np
import pandas as pd
from sim import load


def rth(df):
    ny = df.tz_convert("America/New_York") if False else df.copy()
    ny.index = ny.index.tz_convert("America/New_York")
    mins = ny.index.hour * 60 + ny.index.minute
    ny = ny[(mins >= 570) & (mins < 960)].copy()
    ny["day"] = ny.index.date
    ny["tod"] = ny.index.hour * 60 + ny.index.minute
    return ny


def orb(ny, fee=0.0001, tp_r=10.0):
    trades = []
    for day, g in ny.groupby("day", sort=True):
        if len(g) < 70 or g.tod.iloc[0] != 570:
            continue
        f = g.iloc[0]
        if f.close == f.open:
            continue
        side = 1 if f.close > f.open else -1
        e = g.open.iloc[1]
        stop = f.low if side == 1 else f.high
        R = (e - stop) * side
        if R <= 0:
            continue
        tp = e + side * tp_r * R
        ex, why = g.close.iloc[-1], "eod"
        for _, b in g.iloc[1:].iterrows():
            if side == 1:
                if b.low <= stop: ex, why = min(b.open, stop), "sl"; break
                if b.high >= tp: ex, why = max(b.open, tp), "tp"; break
            else:
                if b.high >= stop: ex, why = max(b.open, stop), "sl"; break
                if b.low <= tp: ex, why = min(b.open, tp), "tp"; break
        r = side * (ex / e - 1) - 2 * fee
        trades.append((pd.Timestamp(day), side, r, why))
    return pd.DataFrame(trades, columns=["day", "side", "ret", "why"])


def noise(ny, fee=0.0001, lookback=14, step=30, start_tod=600, long_only=False):
    days = sorted(ny.day.unique())
    by = {d: g for d, g in ny.groupby("day")}
    # judėjimas nuo dienos open kiekvienu dienos laiku
    mv = {}
    for d in days:
        g = by[d]
        if g.tod.iloc[0] != 570:
            continue
        mv[d] = pd.Series((g.close / g.open.iloc[0] - 1).abs().values, index=g.tod.values)
    trades = []
    prev_close = None
    hist = []
    for d in days:
        g = by[d]
        if d not in mv:
            prev_close = g.close.iloc[-1]; continue
        if len(hist) >= lookback and prev_close is not None and len(g) >= 70:
            sigma = pd.concat(hist[-lookback:], axis=1).mean(axis=1)
            o = g.open.iloc[0]
            up_base, lo_base = max(o, prev_close), min(o, prev_close)
            tp_ = (g.high + g.low + g.close) / 3
            vol = g.volume.replace(0, np.nan).fillna(1)
            vwap = (tp_ * vol).cumsum() / vol.cumsum()
            pos, e = 0, None
            for j in range(len(g)):
                t = g.tod.iloc[j] + 5  # žvakės pabaiga
                last = j == len(g) - 1
                if (t % step == 0 and t >= start_tod) or last:
                    c = g.close.iloc[j]
                    s = sigma.get(g.tod.iloc[j], np.nan)
                    if np.isnan(s):
                        continue
                    U, L = up_base * (1 + s), lo_base * (1 - s)
                    v = vwap.iloc[j]
                    if pos == 1 and (c < max(U, v) or last):
                        trades.append((pd.Timestamp(d), 1, c / e - 1 - 2 * fee)); pos = 0
                    elif pos == -1 and (c > min(L, v) or last):
                        trades.append((pd.Timestamp(d), -1, e / c - 1 - 2 * fee if False else -(c / e - 1) - 2 * fee)); pos = 0
                    if pos == 0 and not last:
                        if c > U:
                            pos, e = 1, c
                        elif c < L and not long_only:
                            pos, e = -1, c
        hist.append(mv[d])
        prev_close = g.close.iloc[-1]
    return pd.DataFrame(trades, columns=["day", "side", "ret"])


def stats(t, a, b):
    t = t[(t.day >= a) & (t.day < b)]
    if not len(t):
        return {}
    yrs = (pd.Timestamp(b) - pd.Timestamp(a)).days / 365.25
    eq = (1 + t.ret).cumprod()
    g, l = t.ret[t.ret > 0].sum(), -t.ret[t.ret < 0].sum()
    yearly = t.groupby(t.day.dt.year).ret.apply(lambda r: round(100 * ((1 + r).prod() - 1), 1)).to_dict()
    return dict(n=len(t), win=round(100 * (t.ret > 0).mean(), 1), cagr=round(100 * (eq.iloc[-1] ** (1 / yrs) - 1), 1),
                dd=round(100 * (1 - eq / eq.cummax()).max(), 1), pf=round(g / l, 2), years=yearly)


def hold(ny, a, b):
    c = ny.close
    c = c[(c.index.tz_localize(None) >= a) & (c.index.tz_localize(None) < b)] if False else c[(pd.to_datetime(ny.day) >= a) & (pd.to_datetime(ny.day) < b)]
    yrs = (pd.Timestamp(b) - pd.Timestamp(a)).days / 365.25
    eq = c / c.iloc[0]
    return dict(cagr=round(100 * ((c.iloc[-1] / c.iloc[0]) ** (1 / yrs) - 1), 1), dd=round(100 * (1 - eq / eq.cummax()).max(), 1))


if __name__ == "__main__":
    D = sys.argv[1]
    for name in sys.argv[2:]:
        ny = rth(load(D, name, "5min"))
        print(f"\n=== {name} ===  laikyti 2021-03..2026-11:", hold(ny, "2021-03-01", "2026-11-10"))
        for lab, t in (("ORB", orb(ny)), ("NOISE", noise(ny)), ("NOISE long", noise(ny, long_only=True))):
            print(f" {lab:10} visas:", stats(t, "2021-03-01", "2026-11-10"))
            print(f" {'':10} 2025+ :", {k: v for k, v in stats(t, "2025-01-01", "2026-11-10").items() if k != "years"})
