#!/usr/bin/env python3
"""#6 Laiko eilučių momentum su volatilumo taikymu (Moskowitz, Ooi, Pedersen 2012).
Kas mėnesį: kiekvienam ETF ženklas = 12 mėn. grąžos virš BIL ženklas; svoris = (tikslinis vol / ETF vol) / N.
Variantai: long-only (neigiamas -> pinigai) ir long-short; bendras svertas apribotas 1x arba 2x.
0,05 % mokestis nuo apyvartos. Laisvi pinigai = BIL. Periodai: 2008–2015 (straipsnio laikas) ir 2016–2026 (po).
Paleisti: ../../quantconnect-lean/.venv/bin/python test.py
"""
from pathlib import Path
import numpy as np, pandas as pd

R = Path(__file__).resolve().parent
FEE = 0.0005
U = ["SPY", "QQQ", "IWM", "EFA", "EEM", "EWJ", "EWG", "EWU", "TLT", "IEF", "SHY", "LQD", "HYG", "TIP",
     "GLD", "SLV", "DBC", "USO", "UNG", "DBA", "UUP", "FXE", "FXY", "FXB", "VNQ"]
T = U + ["BIL", "AGG"]


def load():
    f = R / "data/px.pkl"
    if f.exists():
        return pd.read_pickle(f)
    import yfinance as yf
    d = yf.download(T, start="2003-01-01", end="2026-11-13", auto_adjust=True, progress=False)["Close"]
    d.to_pickle(f)
    return d


C = load().ffill(limit=5)
idx = C.SPY.dropna().index
C = C.reindex(idx)
rets = C.pct_change()
cash = rets.BIL.fillna(0)
cash[C.BIL.isna()] = 0
vol = rets[U].ewm(span=60, min_periods=60).std() * np.sqrt(252)
mom12 = C[U] / C[U].shift(252) - 1
cash12 = (C.BIL / C.BIL.shift(252) - 1).fillna(0)
month_end = idx.to_series().groupby(idx.to_period("M")).last().values


def run(long_short, cap, tvol=0.40, lb=252):
    m = C[U] / C[U].shift(lb) - 1
    sig = np.sign(m.sub((C.BIL / C.BIL.shift(lb) - 1).fillna(0), axis=0))
    if not long_short:
        sig = sig.clip(lower=0)
    avail = m.notna() & vol.notna()
    n = avail.sum(axis=1).replace(0, np.nan)
    w = (sig * (tvol / vol)).where(avail).div(n, axis=0).fillna(0)
    g = w.abs().sum(axis=1)
    w = w.mul(np.minimum(1, cap / g.replace(0, np.nan)).fillna(0), axis=0)
    w = w.loc[month_end].reindex(idx).ffill().fillna(0)
    held = w.shift(1).fillna(0)
    turn = held.diff().abs().sum(axis=1).fillna(0)
    r = (held * rets[U].fillna(0)).sum(axis=1) + (1 - held.abs().sum(axis=1)) * cash - turn * FEE
    return r


def stats(r, a, b):
    r = r[a:b]
    eq = (1 + r).cumprod()
    yrs = len(r) / 252
    cagr = eq.iloc[-1] ** (1 / yrs) - 1
    dd = (eq / eq.cummax() - 1).min()
    sh = r.mean() / r.std() * np.sqrt(252)
    return cagr * 100, dd * 100, sh


rs = {
    "Long-only, 1x": run(False, 1), "Long-only, 2x": run(False, 2),
    "Long-short, 1x": run(True, 1), "Long-short, 2x": run(True, 2),
    "Long-only 6 mėn., 1x": run(False, 1, lb=126), "Long-short 6 mėn., 2x": run(True, 2, lb=126),
    "SPY laikyti": rets.SPY.fillna(0),
    "60/40 SPY/AGG": 0.6 * rets.SPY.fillna(0) + 0.4 * rets.AGG.fillna(0),
}
P = [("2008-01-01", "2015-12-31"), ("2016-01-01", "2026-11-12"), ("2008-01-01", "2026-11-12")]
rows = []
for k, r in rs.items():
    row = [k]
    for a, b in P:
        c, d, s = stats(r, a, b)
        row += [f"{c:+.1f}", f"{d:.0f}", f"{s:.2f}"]
    rows.append(row)
yr = pd.DataFrame({k: (1 + v["2016":]).groupby(v["2016":].index.year).prod() - 1 for k, v in rs.items()}) * 100
hdr = "| Variantas | 08–15 %/m | kritimas | Sharpe | 16–26 %/m | kritimas | Sharpe | 08–26 %/m | kritimas | Sharpe |\n|" + "---|" * 10
out = hdr + "\n" + "\n".join("| " + " | ".join(r) + " |" for r in rows)
out += "\n\nMetai (2016–2026, %):\n\n" + yr.round(1).to_markdown()
print(out)
(R / "REZULTATAI.txt").write_text(out + "\n")
