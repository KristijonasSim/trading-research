#!/usr/bin/env python3
"""#17 Liekamasis (residual) momentum (Blitz, Huij, Martens 2011, J. Empirical Finance).
Kas mėnesį S&P 500 akcijos (tik tuo metu indekse, duomenys kaip #7): 36 mėn. regresija prieš Fama-French 3 faktorius,
signalas = liekanų suma už mėn. t−12..t−2, padalinta iš jų std. Long top 10 %, laikoma 1 arba 6 mėn.
Palyginimas: įprastas 12-1 momentum, lygiavertis krepšelis, SPY. Mokestis 0,1 %. Iki 2026-09 (FF duomenys)."""
import os, numpy as np, pandas as pd
here = os.path.dirname(os.path.abspath(__file__))
os.chdir(os.path.join(here, "../07_lowvol"))
exec(open("test.py").read().split("W = {k")[0])
os.chdir(here)
ff = pd.read_csv("data/F-F_Research_Data_Factors.csv", skiprows=4)
ff = ff[ff.iloc[:, 0].astype(str).str.strip().str.len() == 6].copy()
ff.index = pd.PeriodIndex(pd.to_datetime(ff.iloc[:, 0].astype(str).str.strip(), format="%Y%m"), freq="M")
ff = ff.iloc[:, 1:].astype(float) / 100
mc = C.resample("ME").last(); mr = mc.pct_change(fill_method=None); mr.index = mr.index.to_period("M")
ff = ff.reindex(mr.index)
X = np.column_stack([np.ones(len(ff)), ff[["Mkt-RF", "SMB", "HML"]].values])
ex = mr.sub(ff.RF, axis=0)
score = pd.DataFrame(np.nan, mr.index, mr.columns)
for i in range(36, len(mr)):
    if np.isnan(X[i - 1]).any(): continue
    Y = ex.iloc[i - 36:i].values; Xi = X[i - 36:i]
    ok = ~np.isnan(Y).any(axis=0)
    if ok.sum() == 0: continue
    B, *_ = np.linalg.lstsq(Xi, Y[:, ok], rcond=None)
    E = Y[:, ok] - Xi @ B
    e = E[-12:-1]                      # t−12..t−2 (paskutinis mėnuo praleidžiamas)
    score.iloc[i - 1, np.where(ok)[0]] = e.sum(0) / e.std(0, ddof=1)   # žinoma mėnesio i−1 pabaigoje
mom = mc.shift(1) / mc.shift(12) - 1; mom.index = mom.index.to_period("M")


def target(dt, sig, q=0.1):
    m = [t for t in members(dt) if t in C.columns and not np.isnan(C.at[dt, t])]
    p = pd.Period(dt, "M")
    if p not in sig.index: return pd.Series(dtype=float)
    s = sig.loc[p, m].dropna().sort_values(ascending=False)
    if len(s) < 100: return pd.Series(dtype=float)
    k = int(len(s) * q); return pd.Series(1 / k, s.index[:k])


def bt(sig, hold=1):
    T = {dt: target(dt, sig) for dt in me[:-1]}
    W = pd.DataFrame(0.0, me[:-1], C.columns)
    for j, dt in enumerate(me[:-1]):
        acc = pd.Series(dtype=float)
        for h in range(hold):
            if j - h >= 0 and len(T[me[j - h]]): acc = acc.add(T[me[j - h]] / hold, fill_value=0)
        if len(acc): W.loc[dt, acc.index] = acc.values / acc.sum()
    turn = W.diff().abs().sum(axis=1).reindex(C.index).fillna(0).shift(1).fillna(0)
    held = W.reindex(C.index).ffill().fillna(0).shift(1).fillna(0)
    return ((held * R.fillna(0)).sum(axis=1) - turn * FEE)[days]


def st(r, a, b):
    r = r[a:b]; r = r[r.ne(0).cumsum() > 0]; eq = (1 + r).cumprod(); y = len(r) / 252
    return [f"{(eq.iloc[-1] ** (1 / y) - 1) * 100:+.1f}", f"{(eq / eq.cummax() - 1).min() * 100:.0f}", f"{r.mean() / r.std() * np.sqrt(252):.2f}"]


S = {"Liekamasis momentum top 10 %, 1 mėn.": bt(score, 1), "Liekamasis momentum top 10 %, 6 mėn.": bt(score, 6),
     "12-1 momentum top 10 %, 1 mėn.": bt(mom, 1), "12-1 momentum top 10 %, 6 mėn.": bt(mom, 6)}
ew = pd.DataFrame(0.0, me[:-1], C.columns)
for dt in me[:-1]:
    m = [t for t in members(dt) if t in C.columns and not np.isnan(C.at[dt, t])]; ew.loc[dt, m] = 1 / len(m)
S["Visos (lygiavertis)"] = (ew.reindex(C.index).ffill().fillna(0).shift(1).fillna(0) * R.fillna(0)).sum(axis=1)[days]
S["SPY"] = rs[days].fillna(0)
per = [("2003", "2013"), ("2014", "2026-09"), ("2020", "2026-09")]
out = "| Variantas | " + " | ".join(f"{a}–{b} %/m | kritimas | Sharpe" for a, b in per) + " |\n|" + "---|" * 10 + "\n"
for k, r in S.items():
    out += f"| {k} | " + " | ".join(" | ".join(st(r, a, b)) for a, b in per) + " |\n"
yr = pd.DataFrame({k: (1 + r["2014":]).groupby(r["2014":].index.year).prod() - 1 for k, r in S.items()}).mul(100).round(1)
out += "\nMetai (%):\n\n" + yr.T.to_markdown()
print(out); open("REZULTATAI.txt", "w").write(out + "\n")
