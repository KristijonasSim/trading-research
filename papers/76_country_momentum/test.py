"""76: Šalių akcijų indeksų momentum (Quantpedia „Momentum Effect in Country Equity Indexes“; Asness, Liew, Stevens 1997; Balvers, Wu 2006).
20 iShares šalių ETF, kas mėnesį long top 4 (arba 5) pagal 12-1 mėn. grąžą; variantas su absoliučiu filtru (grąža > BIL, kitaip BIL). Kaštai 0,05 %.
Taip pat šalių žemo volatilumo (12 mėn. dienos std) ir 1 mėn. reversalo variantai. Paleisti: quantconnect-lean/.venv/bin/python papers/76_country_momentum/test.py"""
import os, numpy as np, pandas as pd, yfinance as yf
D = os.path.dirname(os.path.abspath(__file__)); FEE = 0.0005
T = "EWA EWC EWG EWH EWJ EWL EWP EWQ EWS EWU EWW EWY EWZ EWT EWI EWN EWD EWK EWO EZA".split()
f = f"{D}/px.csv"
if not os.path.exists(f): yf.download(T + ["EFA", "SPY", "BIL", "ACWI"], start="1999-01-01", auto_adjust=True, progress=False)["Close"].to_csv(f)
C = pd.read_csv(f, index_col=0, parse_dates=True); M = C.resample("ME").last(); RM = M.pct_change(fill_method=None)
cash = RM.BIL.fillna(0.001)
def run(score, k=4, absf=False):
    out, wprev = [], pd.Series(0.0, T)
    for i in range(13, len(M) - 1):
        s = score.iloc[i][T].dropna()
        if len(s) < 10: out.append(0.0); continue
        top = s.nlargest(k).index; w = pd.Series(0.0, T); w[top] = 1 / k
        if absf:
            mom = M.iloc[i][top] / M.iloc[i - 12][top] - 1; bad = mom[mom < 0].index; w[bad] = 0
        nxt = RM.iloc[i + 1]; r = (w * nxt[T].fillna(0)).sum() + (1 - w.sum()) * cash.iloc[i + 1] - (w - wprev).abs().sum() * FEE
        out.append(r); wprev = w
    return pd.Series(out, M.index[14:])
def st(x, a, b):
    x = x[a:b]; e = (1 + x).cumprod(); y = len(x) / 12
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+5.1f}% kr {(e / e.cummax() - 1).min() * 100:3.0f}%"
PER = [("2001", "2012"), ("2013", "2019"), ("2020", "2026")]
mom = M.shift(1) / M.shift(12) - 1
vol = C[T].pct_change(fill_method=None).rolling(252).std().resample("ME").last()
rev = -RM
ew = RM[T].mean(axis=1)
print("periodai: 2001–12 | 2013–19 | 2020–26")
for nm, x in (("EFA laikyti", RM.EFA), ("SPY laikyti", RM.SPY), ("20 šalių lygiai", ew)): print(f"{nm:30s} " + " | ".join(st(x.fillna(0), a, b) for a, b in PER))
for k in (4, 5):
    print(f"{'momentum 12-1, top ' + str(k):30s} " + " | ".join(st(run(mom, k), a, b) for a, b in PER))
    print(f"{'  + absoliutus filtras':30s} " + " | ".join(st(run(mom, k, True), a, b) for a, b in PER))
print(f"{'žemas volatilumas top 5':30s} " + " | ".join(st(run(-vol, 5), a, b) for a, b in PER))
print(f"{'1 mėn. reversalas top 5':30s} " + " | ".join(st(run(rev, 5), a, b) for a, b in PER))
