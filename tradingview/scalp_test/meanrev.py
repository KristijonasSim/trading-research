"""Intraday atšokimas (Connors RSI(2) principas, pritaikytas 5m/15m, tik 9:30-16:00 NY):
long kai RSI(2) < lo ir kaina žemiau VWAP - a*ATR(14); išeina kai RSI(2) > hi arba kaina >= VWAP, SL = b*ATR, arba 16:00.
short simetriškai. Renkama pagal 2021-24, tikrinama 2025-26."""
import sys, itertools, numpy as np, pandas as pd
from multiprocessing import Pool
from sim import load, rsi, rma
from intraday import rth
FEE = 0.00003
def prep(name, tf, D):
    ny = rth(load(D, name, f"{tf}min"))
    c = ny.close
    tr = pd.concat([ny.high - ny.low, (ny.high - c.shift()).abs(), (ny.low - c.shift()).abs()], axis=1).max(axis=1)
    ny["atr"] = rma(tr, 14); ny["r2"] = rsi(c, 2)
    tp = (ny.high + ny.low + c) / 3; v = ny.volume.replace(0, np.nan).fillna(1)
    ny["vwap"] = (tp * v).groupby(ny.day).cumsum() / v.groupby(ny.day).cumsum()
    ny["last"] = ny.day != ny.day.shift(-1)
    ny["first"] = ny.tod < 570 + 30
    return ny
def run(args):
    ny, lo, a, b, ls = args
    O, H, L, C = ny.open.values, ny.high.values, ny.low.values, ny.close.values
    A, R, V, LA, FI = ny.atr.values, ny.r2.values, ny.vwap.values, ny["last"].values, ny["first"].values
    days = pd.to_datetime(ny.day).values
    res, pos = [], 0
    for i in range(len(ny)):
        if pos:
            ex = None
            if pos == 1 and L[i] <= sl: ex = min(O[i], sl)
            elif pos == -1 and H[i] >= sl: ex = max(O[i], sl)
            elif (pos == 1 and (R[i] > 100 - lo * 3 or C[i] >= V[i])) or (pos == -1 and (R[i] < lo * 3 or C[i] <= V[i])) or LA[i]:
                ex = C[i]
            if ex is not None:
                res.append((days[i], pos * (ex / e - 1) - 2 * FEE)); pos = 0
                continue
        if pos == 0 and not LA[i] and not FI[i] and not np.isnan(A[i]):
            if R[i] < lo and C[i] < V[i] - a * A[i]:
                pos, e, sl = 1, C[i], C[i] - b * A[i]
            elif ls and R[i] > 100 - lo and C[i] > V[i] + a * A[i]:
                pos, e, sl = -1, C[i], C[i] + b * A[i]
    t = pd.DataFrame(res, columns=["day", "ret"])
    return (lo, a, b, ls), st(t, "2021-03-01", "2025-01-01"), st(t, "2025-01-01", "2026-11-10")
def st(t, x, y):
    t = t[(t.day >= x) & (t.day < y)]
    if len(t) < 30: return dict(n=len(t))
    yrs = (pd.Timestamp(y) - pd.Timestamp(x)).days / 365.25; eq = (1 + t.ret).cumprod()
    m = t.groupby(t.day.dt.to_period("M")).ret.apply(lambda r: (1 + r).prod() - 1)
    return dict(n=len(t), win=round(100 * (t.ret > 0).mean()), cagr=round(100 * (eq.iloc[-1] ** (1 / yrs) - 1), 1),
                dd=round(100 * (1 - eq / eq.cummax()).max(), 1), mpos=round(100 * (m > 0).mean()))
if __name__ == "__main__":
    D = sys.argv[1]
    for name in ("NAS100", "SPX500"):
        for tf in (5, 15):
            ny = prep(name, tf, D)
            g = list(itertools.product([5, 10], [0.5, 1.0, 1.5], [1.5, 3.0], [False, True]))
            with Pool(16) as p: R = p.map(run, [(ny, *x) for x in g])
            R = [r for r in R if r[1].get("n", 0) >= 100]
            R.sort(key=lambda r: -r[1]["cagr"] / max(r[1]["dd"], 3))
            print(f"== {name} {tf}m  geriausi pagal 2021-24 ==")
            for r in R[:3]: print("  ", r)
