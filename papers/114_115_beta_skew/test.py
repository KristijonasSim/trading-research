"""114: žemos beta (60 d. beta prieš BTC) monetos; 115: mažiausia 30/60 d. dienos grąžų asimetrija (loterijos vengimas).
Top 50 pagal apyvartą (su išregistruotomis), perbalansavimas kas 7 d., 20 % kraštas, mokestis 0,1 %. Įrankis: papers/xsec.py."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
from xsec import load, run, stats
P, V = load(); R = P.pct_change(fill_method=None); b = R["BTCUSDT"]
def beta(L):
    cov = R.rolling(L, min_periods=L - 10).cov(b); return cov.div(b.rolling(L, min_periods=L - 10).var(), axis=0)
T = {"Top50 lygiais": lambda: run(P, V, lambda p: R, 7, side="bench")}
for L in (60, 120):
    T[f"114 Žema beta {L} d., long"] = lambda L=L: run(P, V, lambda p: -beta(L), 7)
    T[f"114 Žema beta {L} d., long-short"] = lambda L=L: run(P, V, lambda p: -beta(L), 7, side="ls")
for L in (30, 60):
    T[f"115 Maža asimetrija {L} d., long"] = lambda L=L: run(P, V, lambda p: -R.rolling(L, min_periods=L - 5).skew(), 7)
    T[f"115 Maža asimetrija {L} d., long-short"] = lambda L=L: run(P, V, lambda p: -R.rolling(L, min_periods=L - 5).skew(), 7, side="ls")
out = ["# 114/115 Beta ir asimetrija – rezultatai\n", "| Variantas | 2018–21 %/m. | kritimas | 2021–26 %/m. | kritimas | Metai 2021–26 |", "|---|---|---|---|---|---|"]
for n, f in T.items():
    e = f(); s1 = stats(e, "2018-01-01", "2021-11-08"); s2 = stats(e, "2021-11-08", "2026-11-08")
    out.append(f"| {n} | {s1['cagr']:+} | {s1['dd']} % | {s2['cagr']:+} | {s2['dd']} % | {s2['yearly']} |"); print(out[-1], flush=True)
open("rezultatai_raw.md", "w").write("\n".join(out) + "\n")
