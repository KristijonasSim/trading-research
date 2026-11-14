"""66: A) Aukso/sidabro santykio (GSR) rotacija: kai GSR aukštas (z > k) – SLV, kai žemas – GLD (populiarus metalų prekiautojų teiginys).
B) Gundlach vario/aukso santykis: santykis kyla (> N d. vid.) -> SPY (arba QQQ), krenta -> TLT/IEF („risk-on/off“), populiarus nuo ~2016.
Futures HG=F, GC=F, SI=F (Yahoo) signalui, prekyba ETF (GLD, SLV, SPY, TLT, IEF). 1 d. vėlavimas, kaštai 0,03 %.
Paleisti: quantconnect-lean/.venv/bin/python papers/66_gold_ratios/test.py"""
import os, numpy as np, pandas as pd, yfinance as yf
D = os.path.dirname(os.path.abspath(__file__)); FEE = 0.0003
f = f"{D}/px.csv"
if not os.path.exists(f):
    yf.download(["HG=F", "GC=F", "SI=F", "GLD", "SLV", "SPY", "QQQ", "TLT", "IEF", "BIL"], start="2000-01-01", auto_adjust=True, progress=False)["Close"].to_csv(f)
C = pd.read_csv(f, index_col=0, parse_dates=True).ffill(); R = C.pct_change(fill_method=None).fillna(0)
def st(x, a, b):
    x = x[a:b]; e = (1 + x).cumprod(); y = len(x) / 252
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+5.1f}% kr {(e / e.cummax() - 1).min() * 100:3.0f}%"
def rot(w):   # w: DataFrame svorių (signalas dienos t uždarymu), grąža nuo t+1
    w = w.shift(1).fillna(0); x = (w * R[w.columns]).sum(axis=1) - w.diff().abs().sum(axis=1).fillna(0) * FEE; return x
print("== A Aukso/sidabro santykis (GLD/SLV) ==   periodai: 2007–14 | 2015–20 | 2021–26")
PA = [("2007", "2015"), ("2015", "2021"), ("2021", "2027")]
gsr = C["GC=F"] / C["SI=F"]
for nm in ("GLD", "SLV"): print(f"  {nm} laikyti: " + " | ".join(st(R[nm], a, b) for a, b in PA))
for win in (252, 504):
    z = (gsr - gsr.rolling(win).mean()) / gsr.rolling(win).std()
    for k in (0.0, 1.0):
        w = pd.DataFrame(0.0, C.index, ["GLD", "SLV"]); w.loc[z > k, "SLV"] = 1; w.loc[z <= k, "GLD"] = 1
        print(f"  z({win}) > {k}: SLV, kitaip GLD   " + " | ".join(st(rot(w), a, b) for a, b in PA))
print("\n== B Vario/aukso santykis -> SPY/QQQ arba TLT/IEF ==   periodai: 2003–15 | 2016–20 | 2021–26")
PB = [("2003", "2016"), ("2016", "2021"), ("2021", "2027")]
cg = C["HG=F"] / C["GC=F"]
for nm in ("SPY", "QQQ", "TLT"): print(f"  {nm} laikyti: " + " | ".join(st(R[nm], a, b) for a, b in PB))
for n in (50, 100, 200):
    for risk, safe in (("SPY", "TLT"), ("SPY", "IEF"), ("QQQ", "IEF")):
        on = cg > cg.rolling(n).mean(); w = pd.DataFrame(0.0, C.index, [risk, safe]); w.loc[on, risk] = 1; w.loc[~on, safe] = 1
        print(f"  santykis > {n} d. vid.: {risk}, kitaip {safe}  " + " | ".join(st(rot(w), a, b) for a, b in PB))
w = pd.DataFrame(0.5, C.index, ["SPY", "TLT"]); print("  60/40 palyg. (50/50 SPY/TLT): " + " | ".join(st(rot(w), a, b) for a, b in PB))
