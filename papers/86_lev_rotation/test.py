"""86: Sverto ETF momentum rotacija (Reddit r/LETFs, Bogleheads „HFEA + momentum“ variantai): kas mėnesį laikyti geriausią iš {3x QQQ, 3x TLT, 2x GLD}
pagal 1/3/6 mėn. (arba 1-3-6 vidurkio) grąžą; jei geriausio grąža < 0 – BIL. Sintetiniai sverto ETF iš QQQ/TLT/GLD dienos grąžų:
L × r − (L−1) × BIL − 0,95 %/m. valdymo mokestis (2003–2026), kad apimtų 2008. Kaštai 0,05 %. Paleisti: quantconnect-lean/.venv/bin/python papers/86_lev_rotation/test.py"""
import os, numpy as np, pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(D)
L = lambda t: pd.read_csv(f"{R}/59_ibs/data/{t}.csv", index_col=0, parse_dates=True).Close
q, t, g = L("QQQ"), L("TLT"), L("GLD"); bil = L("BIL").pct_change()
idx = q.index[q.index >= "2004-12-01"]; cash = bil.reindex(idx).fillna(0.0001)
def lev(p, k): r = p.reindex(idx).pct_change().fillna(0); return k * r - (k - 1) * cash - 0.0095 / 252
A = pd.DataFrame({"TQQQ": lev(q, 3), "TMF": lev(t, 3), "UGL": lev(g, 2), "BIL": cash})
P = (1 + A).cumprod(); M = P.resample("ME").last(); RM = M.pct_change()
def st(x, a, b):
    x = x[a:b]; e = (1 + x).cumprod(); n = len(x) / 12; return f"{(e.iloc[-1] ** (1 / n) - 1) * 100:+5.1f}% kr {(e / e.cummax() - 1).min() * 100:3.0f}%"
PER = [("2005", "2012"), ("2013", "2019"), ("2020", "2026")]
print("periodai: 2005–12 | 2013–19 | 2020–26 (mėnesinis)")
for c in ("TQQQ", "TMF", "UGL"): print(f"{c + ' (sint.) laikyti':28s} " + " | ".join(st(RM[c].fillna(0), a, b) for a, b in PER))
hf = 0.55 * RM.TQQQ + 0.45 * RM.TMF; print(f"{'55/45 TQQQ/TMF (mėn.)':28s} " + " | ".join(st(hf.fillna(0), a, b) for a, b in PER))
for nm, sc in (("1 mėn.", M.pct_change(1)), ("3 mėn.", M.pct_change(3)), ("6 mėn.", M.pct_change(6)), ("1-3-6 vid.", (M.pct_change(1) + M.pct_change(3) + M.pct_change(6)) / 3)):
    out, prev = [], None
    for i in range(6, len(M) - 1):
        s = sc.iloc[i][["TQQQ", "TMF", "UGL"]]; best = s.idxmax(); pick = best if s[best] > 0 else "BIL"
        r = RM.iloc[i + 1][pick] - (0.0005 * 2 if pick != prev else 0); out.append(r); prev = pick
    x = pd.Series(out, M.index[7:])
    print(f"{'rotacija ' + nm:28s} " + " | ".join(st(x, a, b) for a, b in PER))
