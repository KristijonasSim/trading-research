"""Instagram alanintelligence: JAV akcijos, kai uždarymas < 30 d. vidurkis -> T-bills, kai > -> akcijos (1926-2026).
Duomenys: Kenneth French daily (Mkt-RF + RF = rinkos grąža su dividendais), iki 2026-09.
Tikriname: ar atsikartoja, kaip veikia pagal laikotarpius, su realiais šiandienos kaštais, ir kai prekiaujama kitą dieną."""
from pathlib import Path
import numpy as np, pandas as pd

f = Path(__file__).parent / "data/F-F_Research_Data_Factors_daily.csv"
d = pd.read_csv(f, skiprows=4, index_col=0)
d = d[pd.to_numeric(d.index, errors="coerce").notna()]
d.index = pd.to_datetime(d.index.astype(str), format="%Y%m%d"); d = d.astype(float) / 100
mkt, rf = d["Mkt-RF"] + d.RF, d.RF
px = (1 + mkt).cumprod()


def strat(n, cost, lag):
    sig = (px > px.rolling(n).mean()).astype(float)
    pos = sig.shift(lag)  # lag=1: sprendimas uždaryme, grąža nuo kitos dienos (kaip įraše); lag=2: prekiauti kitos dienos uždaryme
    r = pos * mkt + (1 - pos) * rf - cost * pos.diff().abs().fillna(0)
    return r, pos


def st(r):
    eq = (1 + r).cumprod(); y = len(r) / 252
    return 100 * (eq.iloc[-1] ** (1 / y) - 1), 100 * (1 - eq / eq.cummax()).max(), eq.iloc[-1]


out = []
r0, pos = strat(30, 0, 1)
r0 = r0["1926-08-15":]; h = mkt["1926-08-15":]
out.append(f"Patikra 1926-2026, be kaštų: taisyklė 1000 -> {1000 * st(r0)[2]:,.0f} $, laikymas -> {1000 * st(h)[2]:,.0f} $ "
           f"(įraše 339 873 578 ir 17 677 632), sandorių {int(pos.diff().abs().sum())}, kritimas {st(r0)[1]:.1f} % vs {st(h)[1]:.1f} %")
out.append("\n%/m. pagal laikotarpius (MA30, sprendimas uždaryme):")
out.append(f"{'laikotarpis':12} {'laikyti':>8} {'be kaštų':>9} {'0,02 %':>8} {'0,1 %':>7} {'0,2 %':>7} {'kitą d. 0,02 %':>15} {'kritimas laik./MA30':>21}")
for a, b in (("1926", "1949"), ("1950", "1974"), ("1975", "1999"), ("2000", "2012"), ("2013", "2026"), ("1993", "2026")):
    hh = st(mkt[a:b])
    cols = [st(strat(30, c, 1)[0][a:b])[0] for c in (0, 0.0002, 0.001, 0.002)]
    nxt = st(strat(30, 0.0002, 2)[0][a:b])[0]
    out.append(f"{a}-{b:6} {hh[0]:8.1f} " + " ".join(f"{x:8.1f}" for x in cols) + f" {nxt:14.1f}"
               f"   {hh[1]:6.0f} / {st(strat(30, 0.0002, 1)[0][a:b])[1]:.0f}")
out.append("\nKiti vidurkiai, 2000-2026, 0,02 % kaštai (%/m., kritimas):")
for n in (10, 30, 50, 100, 150, 200):
    s = st(strat(n, 0.0002, 1)[0]["2000":]); out.append(f"  MA{n:3}: {s[0]:5.1f} %/m., kritimas {s[1]:.0f} %")
s = st(mkt["2000":]); out.append(f"  laikyti: {s[0]:5.1f} %/m., kritimas {s[1]:.0f} %")
print("\n".join(out)); (Path(__file__).parent / "REZULTATAI.txt").write_text("\n".join(out))
