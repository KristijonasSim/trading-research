"""99: Dow teorija (C. Dow, W. Hamilton; supaprastinta, populiari forma): akcijos laikomos, kai ir Dow Jones Industrial (^DJI), ir Transportation (^DJT)
virš 200 d. vidurkio (arba abu pasiekė 52 sav. maksimumą per paskutinius 3 mėn. – „patvirtinimas“); išeinama, kai abu žemiau. Prekiaujama SPY (BIL kitu metu).
Palyginimas: vien SPY > 200 d. SMA. Yahoo 1993–2026, 0,03 % kaštai. Paleisti: quantconnect-lean/.venv/bin/python papers/99_dow_theory/test.py"""
import os, numpy as np, pandas as pd, yfinance as yf
D = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(D); f = f"{D}/px.csv"
if not os.path.exists(f): yf.download(["^DJI", "^DJT"], start="1992-01-01", auto_adjust=True, progress=False)["Close"].to_csv(f)
X = pd.read_csv(f, index_col=0, parse_dates=True).ffill()
spy = pd.read_csv(f"{R}/59_ibs/data/SPY.csv", index_col=0, parse_dates=True).Close; bil = pd.read_csv(f"{R}/59_ibs/data/BIL.csv", index_col=0, parse_dates=True).Close.pct_change()
X = X.reindex(spy.index).ffill(); r = spy.pct_change().fillna(0); cash = bil.reindex(spy.index).fillna(0.0001)
def st(x, a, b):
    x = x[a:b]; e = (1 + x).cumprod(); n = len(x) / 252; return f"{(e.iloc[-1] ** (1 / n) - 1) * 100:+5.1f}% kr {(e / e.cummax() - 1).min() * 100:3.0f}%"
PER = [("2001", "2012"), ("2013", "2019"), ("2020", "2026")]
def hyst(up, dn):
    s = pd.Series(np.nan, up.index); s[up] = 1; s[dn] = 0; return s.ffill().fillna(0)
ma = X.rolling(200).mean(); above = X > ma
hi = X >= X.rolling(252).max(); conf = hi.rolling(63).max().astype(bool)
lo = X <= X.rolling(252).min(); confd = lo.rolling(63).max().astype(bool)
rules = {"SPY laikyti": pd.Series(1.0, spy.index),
         "abu > 200 d. SMA (Dow, supapr.)": hyst(above.all(axis=1), (~above).all(axis=1)),
         "52 sav. maks. patvirtinimas": hyst(conf.all(axis=1), confd.all(axis=1)),
         "palyg.: SPY > 200 d. SMA": (spy > spy.rolling(200).mean()).astype(float)}
print("periodai: 2001–12 | 2013–19 | 2020–26")
for nm, pos in rules.items():
    p1 = pos.shift(1).fillna(0); x = p1 * r + (1 - p1) * cash - pos.diff().abs().fillna(0) * 0.0003
    print(f"{nm:34s} " + " | ".join(st(x, a, b) for a, b in PER) + f" | rinkoje {pos['2001':].mean()*100:.0f}%")
