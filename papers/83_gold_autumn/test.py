"""83: Aukso rudens efektas (Baur 2013 „The autumn effect of gold“, Research in International Business and Finance): rugsėjo ir lapkričio grąžos
reikšmingai teigiamos (1981–2010). Taisyklė: laikyti GLD rugsėjį–lapkritį (arba tik rugsėjį ir lapkritį), kitu metu BIL. Kaštai 0,03 %.
GC=F (futures, 2000+) mėnesių statistikai, GLD (2005+) strategijai. Nematytas po paskelbimo 2013–2026. Paleisti: quantconnect-lean/.venv/bin/python papers/83_gold_autumn/test.py"""
import os, numpy as np, pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(D)
C = pd.read_csv(f"{R}/66_gold_ratios/px.csv", index_col=0, parse_dates=True)
gc = C["GC=F"].dropna(); m = gc.resample("ME").last().pct_change().dropna()
print("GC=F mėnesių vid. grąža % (2001–12 | 2013–26):")
for k in range(1, 13):
    a, b = m[(m.index.month == k) & (m.index.year <= 2012)], m[(m.index.month == k) & (m.index.year >= 2013)]
    print(f"  {k:2d}: {a.mean()*100:+5.2f} ({(a > 0).mean()*100:3.0f}% teig.) | {b.mean()*100:+5.2f} ({(b > 0).mean()*100:3.0f}%)")
gld = C.GLD.dropna(); r = gld.pct_change().fillna(0); bil = C.BIL.reindex(gld.index).pct_change().fillna(0)
def st(x, a, b):
    x = x[a:b]; e = (1 + x).cumprod(); n = len(x) / 252; return f"{(e.iloc[-1] ** (1 / n) - 1) * 100:+5.1f}% kr {(e / e.cummax() - 1).min() * 100:3.0f}%"
PER = [("2005", "2012"), ("2013", "2019"), ("2020", "2026")]
print("\nperiodai: 2005–12 | 2013–19 | 2020–26")
mon = gld.index.month
for nm, mask in (("GLD laikyti", np.ones(len(gld), bool)), ("rugsėjis–lapkritis", np.isin(mon, [9, 10, 11])), ("rugsėjis + lapkritis", np.isin(mon, [9, 11])),
                 ("be rugsėjo–lapkričio", ~np.isin(mon, [9, 10, 11]))):
    pos = pd.Series(mask, gld.index).astype(float); x = pos * r + (1 - pos) * bil - pos.diff().abs().fillna(0) * 0.0003
    print(f"  {nm:22s} " + " | ".join(st(x, a, b) for a, b in PER) + f" | rinkoje {pos.mean()*100:.0f}%")
