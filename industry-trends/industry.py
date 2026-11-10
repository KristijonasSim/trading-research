"""A Century of Profitable Industry Trends (Zarattini & Antonacci 2024) – kopija pagal straipsnį.
Duomenys: Ken French 48 pramonės šakų dienos grąžos (value-weighted) + rizikos neturinti palūkanų norma.

Įėjimas: kaina >= vakarykštė UpperBand = min(Donchian20 max, EMA20 + 1.4*2*vid|ΔP|20).
Stop: LowerBand = max(Donchian40 min, EMA40 − 1.4*2*vid|ΔP|40); stop niekada nemažinamas; išeina, kai kaina < stop.
Dydis: w = (1.5%/N) / σ14 (dienos), suma ≤ 200 %. Perbalansuojama kasdien. Grynieji ir skolinimasis = RF.
Naudojimas: python industry.py <ff dir>
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd


def read_ff(path, section_start):
    lines = Path(path).read_text().splitlines()
    i = next(k for k, l in enumerate(lines) if section_start in l)
    if "," in lines[i]:  # pati eilutė yra antraštė
        i -= 1
    hdr = lines[i + 1]
    rows = []
    for l in lines[i + 2:]:
        if not l.strip() or not l.strip()[0].isdigit():
            break
        rows.append(l)
    from io import StringIO
    df = pd.read_csv(StringIO(hdr + "\n" + "\n".join(rows)), index_col=0)
    df.index = pd.to_datetime(df.index.astype(str), format="%Y%m%d")
    df = df.replace([-99.99, -999], np.nan) / 100
    return df


def run(R, rf, cost=0.0, tv=0.015, cap=2.0):
    P = (1 + R.fillna(0)).cumprod().where(R.notna())
    dP = P.diff().abs()
    up = np.minimum(P.rolling(20).max(), P.ewm(span=20, adjust=False).mean() + 2.8 * dP.rolling(20).mean())
    lo = np.maximum(P.rolling(40).min(), P.ewm(span=40, adjust=False).mean() - 2.8 * dP.rolling(40).mean())
    vol = R.rolling(14).std()
    Pv, upv, lov = P.values, up.values, lo.values
    T, J = P.shape
    pos = np.zeros((T, J))
    stop = np.full(J, np.nan)
    inpos = np.zeros(J, bool)
    for t in range(1, T):
        p = Pv[t]
        ex = inpos & (p < stop)
        inpos[ex] = False
        en = (~inpos) & (p >= upv[t - 1])
        en &= ~np.isnan(p) & ~np.isnan(upv[t - 1])
        inpos[en] = True
        stop[en] = lov[t][en]
        stop[inpos] = np.fmax(stop[inpos], lov[t][inpos])
        inpos[np.isnan(p)] = False
        pos[t] = inpos
    N = R.notna().sum(axis=1).clip(lower=1).values[:, None]
    w = (tv / N) / vol.values * pos
    w = np.nan_to_num(w)
    tot = w.sum(axis=1, keepdims=True)
    w = np.where(tot > cap, w / tot * cap, w)
    W = pd.DataFrame(w, R.index, R.columns)
    Wp = W.shift(1).fillna(0)
    gross = (Wp * R.fillna(0)).sum(axis=1)
    ret = gross + (1 - Wp.sum(axis=1)) * rf - W.diff().abs().sum(axis=1).fillna(0) * cost
    return ret, W


def st(r, a, b):
    r = r[a:b]
    if len(r) < 50:
        return "-"
    eq = (1 + r).cumprod(); y = len(r) / 252
    return f"{100*(eq.iloc[-1]**(1/y)-1):5.1f}%/m krit.{100*(1-eq/eq.cummax()).max():3.0f}%"


if __name__ == "__main__":
    d = sys.argv[1]
    R = read_ff(f"{d}/48_Industry_Portfolios_Daily.csv", "Average Value Weighted Returns -- Daily")
    F = read_ff(f"{d}/F-F_Research_Data_Factors_daily.csv", "Mkt-RF")
    F = F.reindex(R.index)
    mkt, rf = F["Mkt-RF"] + F["RF"], F["RF"].fillna(0)
    print("duomenys:", R.index[0].date(), "–", R.index[-1].date())
    P = [("1926-07-01", "1999-12-31"), ("2000-01-01", "2014-12-31"), ("2015-01-01", "2024-09-30"),
         ("2024-10-01", "2026-12-31"), ("1926-07-01", "2026-12-31")]
    print(" " * 30 + " | ".join(f"{a[:7]}..{b[:7]}".ljust(19) for a, b in P))
    print(f"{'rinka (laikyti)':30}" + " | ".join(st(mkt, a, b).ljust(19) for a, b in P))
    for lab, kw in [("straipsnis, be kaštų", {}), ("kaštai 0,05 %", dict(cost=0.0005)), ("kaštai 0,10 %", dict(cost=0.001)),
                    ("be sverto (cap 100 %)", dict(cap=1.0, cost=0.0005))]:
        r, W = run(R, rf, **kw)
        print(f"{lab:30}" + " | ".join(st(r, a, b).ljust(19) for a, b in P))
        if lab.startswith("kaštai 0,05"):
            yr = r["2015":].groupby(r["2015":].index.year).apply(lambda x: round(100 * ((1 + x).prod() - 1), 1))
            yrm = mkt["2015":].groupby(mkt["2015":].index.year).apply(lambda x: round(100 * ((1 + x).prod() - 1), 1))
            print("   metai (strategija / rinka):", {k: (yr[k], yrm[k]) for k in yr.index})
            print("   vid. bendra pozicija %.0f%%, apyvarta per metus %.0f×" % (100 * W.sum(axis=1)["2000":].mean(), W.diff().abs().sum(axis=1)["2000":].sum() / 26.7))
