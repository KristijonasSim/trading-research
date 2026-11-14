"""101: Infliacijos režimo rotacija (makro „regime“ teiginys; pvz. Neville ir kt. 2021 „The Best Strategies for Inflationary Times“): kai CPI YoY kyla
(YoY > jo 6 mėn. vidurkis arba YoY > 3 %), laikyti GLD (arba 50/50 GLD/DBC), kitaip SPY. CPI skelbiamas ~2 sav. po mėnesio – naudojamas su 1,5 mėn. vėlavimu.
Mėnesinis perbalansavimas, 0,05 % kaštai. 2006–2026. Paleisti: quantconnect-lean/.venv/bin/python papers/101_inflation_regime/test.py"""
import os, pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(D); ROOT = os.path.dirname(R)
cpi = pd.read_csv(f"{D}/CPI.csv", index_col=0, parse_dates=True).iloc[:, 0]
yoy = cpi.pct_change(12); avail = yoy.copy(); avail.index = avail.index + pd.DateOffset(months=1, days=14)
E = pd.read_csv(f"{ROOT}/etf-rotation/data/close.csv", index_col=0, parse_dates=True)
M = E[["SPY", "GLD", "DBC", "TLT"]].resample("ME").last(); RM = M.pct_change()
sig_up = (avail > avail.rolling(6).mean()).reindex(M.index, method="ffill"); sig_hi = (avail > 0.03).reindex(M.index, method="ffill")
def st(x, a, b):
    x = x[a:b].dropna(); e = (1 + x).cumprod(); n = len(x) / 12; return f"{(e.iloc[-1] ** (1 / n) - 1) * 100:+5.1f}% kr {(e / e.cummax() - 1).min() * 100:3.0f}%"
PER = [("2007", "2014"), ("2015", "2020"), ("2021", "2026")]
print("periodai: 2007–14 | 2015–20 | 2021–26")
for c in ("SPY", "GLD"): print(f"{c + ' laikyti':36s} " + " | ".join(st(RM[c], a, b) for a, b in PER))
for nm, s in (("YoY kyla -> GLD, kitaip SPY", sig_up), ("YoY > 3 % -> GLD, kitaip SPY", sig_hi)):
    for alt, lab in (("GLD", "GLD"), ("MIX", "50/50 GLD/DBC")):
        a_r = RM.GLD if alt == "GLD" else 0.5 * RM.GLD + 0.5 * RM.DBC
        s1 = s.shift(1).fillna(False).astype(bool); x = a_r.where(s1, RM.SPY) - (s1 != s1.shift(1)).astype(float) * 0.0005
        print(f"{nm.replace('GLD', lab):36s} " + " | ".join(st(x, a, b) for a, b in PER) + f" | infliacijos režime {s1.mean()*100:.0f}%")
