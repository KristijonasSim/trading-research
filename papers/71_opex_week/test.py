"""71: Opcionų galiojimo savaitės efektas (Stivers, Sun 2013 „Returns and option activity over the option-expiration week for S&P 100 stocks“):
OpEx savaitė (pirmadienis–penktadienis su trečiuoju mėnesio penktadieniu) uždirba daugiau, savaitė po jos – silpna.
Taisyklė: laikyti tik OpEx savaitę (įeinama ankstesnio penktadienio uždarymu), kitu metu BIL. SPY/QQQ (Yahoo) ir 3x (UPRO/TQQQ, etf-rotation).
Kaštai 0,03 %. Paleisti: quantconnect-lean/.venv/bin/python papers/71_opex_week/test.py"""
import os, numpy as np, pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(D); ROOT = os.path.dirname(R); FEE = 0.0003
L = lambda t: pd.read_csv(f"{R}/59_ibs/data/{t}.csv", index_col=0, parse_dates=True).Close
E = pd.read_csv(f"{ROOT}/etf-rotation/data/close.csv", index_col=0, parse_dates=True)
bil = L("BIL").pct_change()
def opex_week(idx):
    s = pd.Series(idx, idx); fr = []
    for (y, m), g in s.groupby([idx.year, idx.month]):
        cal = pd.date_range(f"{y}-{m:02d}-01", periods=31, freq="D"); fridays = cal[(cal.day_of_week == 4) & (cal.month == m)]; fr.append(fridays[2])
    fr = pd.DatetimeIndex(fr); wk = idx.to_period("W-FRI"); return pd.Series(wk.isin(fr.to_period("W-FRI")), idx)
def st(x, a, b):
    x = x[a:b].dropna(); e = (1 + x).cumprod(); y = len(x) / 252
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+5.1f}% kr {(e / e.cummax() - 1).min() * 100:3.0f}%"
PER = [("2001", "2012"), ("2013", "2019"), ("2020", "2026")]
print("periodai: 2001–12 | 2013–19 | 2020–26")
for nm, c in (("SPY", L("SPY")), ("QQQ", L("QQQ")), ("UPRO", E.UPRO.dropna()), ("TQQQ", E.TQQQ.dropna())):
    r = c.pct_change().fillna(0); ow = opex_week(c.index).astype(float); cash = bil.reindex(c.index).fillna(0)
    after = ow.shift(5).fillna(0)  # apytiksliai savaitė po OpEx
    print(f"\n{nm} laikyti: " + " | ".join(st(r, a, b) for a, b in PER))
    print(f"  vid. d. grąža bp: OpEx sav. " + " | ".join(f"{r[ow == 1][a:b].mean()*1e4:+5.1f}" for a, b in PER) + "   kitos: " + " | ".join(f"{r[ow == 0][a:b].mean()*1e4:+5.1f}" for a, b in PER))
    for lab, pos in (("tik OpEx savaitė", ow), ("visos išskyrus OpEx", 1 - ow)):
        x = pos * r + (1 - pos) * cash - pos.diff().abs().fillna(0) * FEE
        print(f"  {lab:22s} " + " | ".join(st(x, a, b) for a, b in PER) + f" | rinkoje {pos.mean()*100:.0f}%")
