"""82: Prezidento rinkimų ciklas (Hirsch, Stock Trader's Almanac; Booth & Booth 2003): kadencijos 3-i metai (priešrinkiminiai) stipriausi,
2-i (vidurio) silpni; populiari taisyklė „pirk vidurio kadencijos metų spalį, laikyk iki priešrinkiminių metų pabaigos“.
^GSPC (be dividendų) 1928–2026, ne rinkoje – 0 % (konservatyviai, be palūkanų). Paleisti: quantconnect-lean/.venv/bin/python papers/82_election_cycle/test.py"""
import os, numpy as np, pandas as pd, yfinance as yf
D = os.path.dirname(os.path.abspath(__file__)); f = f"{D}/gspc.csv"
if not os.path.exists(f): yf.download("^GSPC", start="1927-12-01", auto_adjust=True, progress=False, multi_level_index=False).to_csv(f)
p = pd.read_csv(f, index_col=0, parse_dates=True).Close; y = p.resample("YE").last().pct_change().dropna()
cyc = (y.index.year - 1) % 4 + 1      # 1 = po rinkimų, 2 = vidurio, 3 = priešrinkiminiai, 4 = rinkimų (1928 % 4 == 0 -> 4)
cyc = pd.Series([(yr % 4) or 4 for yr in y.index.year], y.index).map({1: 1, 2: 2, 3: 3, 4: 4})
print("vidutinė metų grąža pagal kadencijos metus (1929–1975 | 1976–2003 | 2004–2025):")
for k, nm in ((1, "po rinkimų"), (2, "vidurio"), (3, "priešrinkiminiai"), (4, "rinkimų")):
    print(f"  {nm:17s} " + " | ".join(f"{y[(cyc == k) & (y.index.year >= a) & (y.index.year <= b)].mean()*100:+6.1f}% (n={((cyc == k) & (y.index.year >= a) & (y.index.year <= b)).sum()})" for a, b in ((1929, 1975), (1976, 2003), (2004, 2025))))
r = p.pct_change().fillna(0); yrs = p.index.year; mon = p.index.month
def st(x, a, b):
    x = x[a:b]; e = (1 + x).cumprod(); n = len(x) / 252; return f"{(e.iloc[-1] ** (1 / n) - 1) * 100:+5.1f}% kr {(e / e.cummax() - 1).min() * 100:3.0f}%"
PER = [("1929", "1975"), ("1976", "2003"), ("2004", "2026")]
def show(nm, pos):
    pos = pd.Series(pos, p.index).astype(float).shift(1).fillna(0); print(f"{nm:44s} " + " | ".join(st(pos * r, a, b) for a, b in PER) + f" | rinkoje {pos.mean()*100:.0f}%")
print("\nperiodai: 1929–75 | 1976–2003 (po Hirsch 1968/Almanac) | 2004–26")
show("laikyti", np.ones(len(p)))
show("be vidurio kadencijos metų", (yrs % 4) != 2)
show("tik priešrinkiminiai metai", (yrs % 4) == 3)
show("vidurio metų spalis -> priešrinkiminių pabaiga", (((yrs % 4) == 2) & (mon >= 10)) | ((yrs % 4) == 3))
show("vidurio spalis -> rinkimų metų pabaiga", (((yrs % 4) == 2) & (mon >= 10)) | ((yrs % 4) == 3) | ((yrs % 4) == 0))
