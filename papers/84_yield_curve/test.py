"""84: Pajamingumo kreivės inversija (Estrella, Mishkin 1996; populiarus recesijos signalas). Taisyklės: A) grynieji kai T10Y2Y (arba T10Y3M) < 0;
B) grynieji 12 mėn. po kreivės „atsitiesimo“ (inversija baigiasi – recesija dažnai prasideda tada); C) grynieji nuo inversijos pradžios iki 18 mėn. po jos pabaigos.
^GSPC (be dividendų), ne rinkoje 0 %, 1 d. vėlavimas. Paleisti: quantconnect-lean/.venv/bin/python papers/84_yield_curve/test.py"""
import os, numpy as np, pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(D)
p = pd.read_csv(f"{R}/82_election_cycle/gspc.csv", index_col=0, parse_dates=True).Close; r = p.pct_change().fillna(0)
def st(x, a, b):
    x = x[a:b]; e = (1 + x).cumprod(); n = len(x) / 252; return f"{(e.iloc[-1] ** (1 / n) - 1) * 100:+5.1f}% kr {(e / e.cummax() - 1).min() * 100:3.0f}%"
PER = [("1977", "2000"), ("2000", "2013"), ("2013", "2027")]
print("periodai: 1977–99 | 2000–12 | 2013–26")
print(f"{'laikyti':40s} " + " | ".join(st(r, a, b) for a, b in PER))
for s in ("T10Y2Y", "T10Y3M"):
    y = pd.read_csv(f"{D}/{s}.csv", index_col=0, parse_dates=True, na_values=".").iloc[:, 0].dropna().reindex(p.index, method="ffill")
    inv = (y < 0)
    def show(nm, out):
        pos = (~out).astype(float).shift(1).fillna(1); print(f"{s} {nm:33s} " + " | ".join(st(pos * r, a, b) for a, b in PER) + f" | rinkoje {pos['1977':].mean()*100:.0f}%")
    show("A grynieji kai < 0", inv)
    end = inv.astype(int).diff() == -1     # inversija baigėsi
    for months in (12, 18):
        out = pd.Series(False, p.index)
        for t in p.index[end]: out[(p.index > t) & (p.index <= t + pd.DateOffset(months=months))] = True
        show(f"B grynieji {months} mėn. po atsitiesimo", out)
        show(f"C inversija + {months} mėn. po", out | inv)
    print(f"   {s} inversijų pabaigos (≥ 20 d. inversijos):", [t.date() for t in p.index[end] if inv[:t].iloc[-21:-1].all()])
