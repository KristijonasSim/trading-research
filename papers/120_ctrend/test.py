"""120: CTREND (Fieberg, Liedtke, Poddig, Walker, Zaremba; JFQA 2024) supaprastintai: ~20 techninių signalų
(kaina / SMA 3–200 d., momentum 1–8 sav., apyvarta / jos SMA, volatilumas), skerspjūviškai standartizuoti (rangai).
Kas savaitę skerspjūvio regresija: kitos savaitės grąža ~ signalai; koeficientai vidurkinami per 52 sav. (tik praeitis),
prognozė = signalai x vid. koef. Top 50 pagal apyvartą, long top 20 % arba long-short. Mokestis 0,1 %."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, pandas as pd
from xsec import load, run, stats
P, V = load()
S = {}
for n in (3, 5, 10, 20, 50, 100, 200): S[f"ma{n}"] = P / P.rolling(n, min_periods=n).mean()
for n in (7, 14, 28, 56): S[f"mom{n}"] = P.pct_change(n, fill_method=None)
for n in (5, 20, 50): S[f"vol{n}"] = V / V.rolling(n, min_periods=n).mean()
S["sd20"] = P.pct_change(fill_method=None).rolling(20).std()
S["max7"] = P.pct_change(fill_method=None).rolling(7).max()
liq = V.rolling(30, min_periods=20).mean(); age = P.notna().cumsum()
R7f = P.pct_change(7, fill_method=None).shift(-7)  # tik regresijos taikiniui (praeities langui), ne signalui
days = P.index[220::7]
coefs = {}; F = pd.DataFrame(np.nan, index=P.index, columns=P.columns)
for t in days:
    ok = (age.loc[t] >= 60) & liq.loc[t].notna(); uni = liq.loc[t][ok].nlargest(50).index
    X = pd.DataFrame({k: v.loc[t, uni].rank(pct=True) - 0.5 for k, v in S.items()}).fillna(0)
    # koeficientas apskaičiuojamas, kai taikinys jau žinomas (t+7), tad naudojamas tik nuo t+7
    y = R7f.loc[t, uni]; m = y.notna()
    if m.sum() > 20:
        b = np.linalg.lstsq(np.c_[np.ones(m.sum()), X[m].values], y[m].values, rcond=None)[0][1:]
        coefs[t + pd.Timedelta(days=7)] = b
    known = [v for k, v in coefs.items() if k <= t][-52:]
    if len(known) >= 26: F.loc[t, uni] = X.values @ np.mean(known, axis=0)
F = F.dropna(how="all").reindex(P.index).ffill(limit=6)
sig = lambda p: F
T = {"Top50 lygiais": lambda: run(P, V, lambda p: p.pct_change(7, fill_method=None), 7, side="bench"),
     "CTREND long top 20 %": lambda: run(P, V, sig, 7), "CTREND long-short": lambda: run(P, V, sig, 7, side="ls"),
     "CTREND long top 20 %, top 20 monetų": lambda: run(P, V, sig, 7, topn=20)}
out = ["# 120 CTREND – rezultatai\n", "| Variantas | 2018–21 %/m. | kritimas | 2021–26 %/m. | kritimas | Metai 2021–26 |", "|---|---|---|---|---|---|"]
for n, f in T.items():
    e = f(); s1 = stats(e, "2019-01-01", "2021-11-08"); s2 = stats(e, "2021-11-08", "2026-11-08")
    out.append(f"| {n} | {s1['cagr']:+} | {s1['dd']} % | {s2['cagr']:+} | {s2['dd']} % | {s2['yearly']} |"); print(out[-1], flush=True)
open("rezultatai_raw.md", "w").write("\n".join(out) + "\n")
