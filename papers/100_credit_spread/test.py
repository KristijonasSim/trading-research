"""100: Kredito skirtumo rinkos laikas (Gilchrist, Zakrajšek 2012; populiarus „high yield spread“ signalas): Moody's Baa − 10 m. iždo skirtumas (FRED BAA10Y, nuo 1986; ICE HY OAS FRED duoda tik 3 m.).
Taisyklės: laikyti SPY (arba QQQ), kai OAS < jo 200 d. vidurkis, arba kai OAS 20 d. pokytis < 0; kitu metu BIL. 1 d. vėlavimas (FRED skelbia kitą dieną), 0,03 %.
Paleisti: quantconnect-lean/.venv/bin/python papers/100_credit_spread/test.py"""
import os, pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(D)
oas = pd.read_csv(f"{D}/BAA10Y.csv", index_col=0, parse_dates=True, na_values=".").iloc[:, 0].dropna()
L = lambda t: pd.read_csv(f"{R}/59_ibs/data/{t}.csv", index_col=0, parse_dates=True).Close
bil = L("BIL").pct_change()
def st(x, a, b):
    x = x[a:b]; e = (1 + x).cumprod(); n = len(x) / 252; return f"{(e.iloc[-1] ** (1 / n) - 1) * 100:+5.1f}% kr {(e / e.cummax() - 1).min() * 100:3.0f}%"
PER = [("2001", "2012"), ("2013", "2019"), ("2020", "2026")]
print("periodai: 2001–12 | 2013–19 | 2020–26")
for t in ("SPY", "QQQ"):
    c = L(t); r = c.pct_change().fillna(0); cash = bil.reindex(c.index).fillna(0.0001); o = oas.reindex(c.index).ffill().shift(1)
    def show(nm, pos):
        p1 = pos.shift(1).fillna(0); x = p1 * r + (1 - p1) * cash - pos.diff().abs().fillna(0) * 0.0003
        print(f"{t} {nm:30s} " + " | ".join(st(x, a, b) for a, b in PER) + f" | rinkoje {pos['2001':].mean()*100:.0f}%")
    print(); show("laikyti", pd.Series(1.0, c.index))
    for n in (50, 200): show(f"skirtumas < {n} d. vidurkis", (o < o.rolling(n).mean()).astype(float))
    show("skirtumo 20 d. pokytis < 0", (o.diff(20) < 0).astype(float))
    show("skirtumas < 3 %", (o < 3).astype(float))
    show("palyg.: kaina > 200 d. SMA", (c > c.rolling(200).mean()).astype(float))
