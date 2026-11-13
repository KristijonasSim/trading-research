"""Aberration ant 25 ETF (../06_tsmom/data/px.pkl), lygios dalys, tik long, mokestis 0,05 %; palyginimas SPY ir 60/40."""
import numpy as np, pandas as pd
C = pd.read_pickle("../06_tsmom/data/px.pkl").ffill(limit=5)
U = ["SPY", "QQQ", "IWM", "EFA", "EEM", "EWJ", "EWG", "EWU", "TLT", "IEF", "SHY", "LQD", "HYG", "TIP", "GLD", "SLV", "DBC", "USO", "UNG", "DBA", "UUP", "FXE", "FXY", "FXB", "VNQ"]
FEE = 0.0005
R = C.pct_change()
out = {}
for n, k in [(35, 2.0), (50, 2.5), (60, 2.5)]:
    W = pd.DataFrame(0.0, C.index, U)
    for s in U:
        c = C[s]; m = c.rolling(n).mean(); sd = c.rolling(n).std(); p = 0; pos = []
        for ci, mi, si in zip(c.values, m.values, sd.values):
            if np.isnan(mi): pos.append(0); continue
            if p == 0 and ci > mi + k * si: p = 1
            elif p == 1 and ci < mi: p = 0
            pos.append(p)
        W[s] = pos
    avail = C[U].notna().sum(axis=1).replace(0, np.nan)
    w = W.div(avail, axis=0).shift(1).fillna(0)
    out[f"Aberration {n}/{k}"] = (w * R[U].fillna(0)).sum(axis=1) - w.diff().abs().sum(axis=1).fillna(0) * FEE
out["SPY"] = R.SPY.fillna(0); out["60/40"] = 0.6 * R.SPY.fillna(0) + 0.4 * R.AGG.fillna(0)
def st(r, a, b):
    r = r[a:b]; eq = (1 + r).cumprod(); y = len(r) / 252
    return f"{(eq.iloc[-1] ** (1 / y) - 1) * 100:+.1f} ({(eq / eq.cummax() - 1).min() * 100:.0f})"
for k, r in out.items(): print(f"| {k} | {st(r, '2008', '2015')} | {st(r, '2016', '2026')} |")
