"""63: Sverto ETF nusidėvėjimo (volatility decay) sandoris: short 3x bull + short 3x bear lygiomis sumomis, perbalansavimas kas mėnesį/savaitę.
Poros: TQQQ/SQQQ, UPRO/SPXU, SOXL/SOXS, TNA/TZA. Skolinimosi kaštai metams 0/3/8 % (bear ETF dažnai brangūs), short pajamos (BIL) įskaitomos 50 %.
Bendra short ekspozicija 100 % kapitalo (po 50 %). Paleisti: quantconnect-lean/.venv/bin/python papers/63_letf_decay/test.py"""
import os, numpy as np, pandas as pd, yfinance as yf
D = os.path.dirname(os.path.abspath(__file__))
T = ["TQQQ", "SQQQ", "UPRO", "SPXU", "SOXL", "SOXS", "TNA", "TZA", "BIL"]
f = f"{D}/px.csv"
if not os.path.exists(f): yf.download(T, start="2010-01-01", auto_adjust=True, progress=False)["Close"].to_csv(f)
C = pd.read_csv(f, index_col=0, parse_dates=True); R = C.pct_change(fill_method=None)
def st(x, a, b):
    x = x[a:b].dropna()
    if len(x) < 100: return "   –"
    e = (1 + x).cumprod(); y = len(x) / 252
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+5.1f}% kr {(e / e.cummax() - 1).min() * 100:3.0f}%"
PER = [("2011", "2016"), ("2017", "2021"), ("2022", "2026")]
print("periodai: 2011–16 | 2017–21 | 2022–26")
for bull, bear in (("TQQQ", "SQQQ"), ("UPRO", "SPXU"), ("SOXL", "SOXS"), ("TNA", "TZA")):
    d = R[[bull, bear]].dropna(); cash = R.BIL.reindex(d.index).fillna(0)
    for freq in ("ME", "W"):
        for borrow in (0.0, 0.03, 0.08):
            # short pozicijų vertės tarp perbalansavimų: kiekviena prasideda -0,5, kinta su ETF kaina
            out = []
            for _, g in d.groupby(pd.Grouper(freq=freq)):
                if g.empty: continue
                path = (1 + g).cumprod()
                pnl = -0.5 * (path - 1).sum(axis=1)                  # short P/L nuo perbalansavimo
                days = np.arange(1, len(g) + 1)
                daily_eq = (1 + pnl - borrow * days / 252 + 0.5 * cash.loc[g.index].cumsum()).values
                rr = pd.Series(daily_eq, g.index).pct_change(); rr.iloc[0] = daily_eq[0] - 1
                rr.iloc[0] -= 0.0004                                  # perbalansavimo kaštai
                out.append(rr)
            x = pd.concat(out)
            print(f"{bull}/{bear} {freq:2s} skolinimasis {borrow*100:.0f}%: " + " | ".join(st(x, a, b) for a, b in PER))
