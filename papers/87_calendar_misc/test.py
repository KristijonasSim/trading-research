"""87: Smulkūs kalendoriaus efektai: A) prieššventinė diena (Ariel 1990; Lakonishok, Smidt 1988), B) algų dienos (Ma, Pohlman 2008 / Quantpedia „Payday anomaly“:
1–2 ir 15–16 mėnesio dienos), C) pirmadienio efektas (French 1980: pirmadienio grąža neigiama). ^GSPC 1950–2026 (be dividendų).
Šventė = darbo diena be prekybos (kai trūksta darbo dienos indekse). Vidutinė dienos grąža bp ir t, periodai prieš/po paskelbimo.
Paleisti: quantconnect-lean/.venv/bin/python papers/87_calendar_misc/test.py"""
import os, numpy as np, pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(D)
p = pd.read_csv(f"{R}/82_election_cycle/gspc.csv", index_col=0, parse_dates=True).Close; p = p[p.index >= "1950-01-01"]; r = p.pct_change().dropna()
bd = pd.bdate_range(r.index[0], r.index[-1]); missing = bd.difference(r.index)
nxt = pd.Series(r.index[1:].append(pd.DatetimeIndex([r.index[-1] + pd.Timedelta(days=1)])), r.index)
preh = pd.Series([any((m > t) and (m < n) for m in missing[(missing > t) & (missing < n)]) for t, n in nxt.items()], r.index)
dom = pd.Series(r.index.day, r.index)
pay = pd.Series(False, r.index)
for (y, m), g in r.groupby([r.index.year, r.index.month]):
    idx = g.index; first2 = idx[:2]; mid = idx[idx.day >= 15][:2]; pay[first2] = True; pay[mid] = True
mon = pd.Series(r.index.day_of_week == 0, r.index)
def stat(mask, a, b):
    x, y = r[mask][a:b], r[~mask][a:b]; d = x.mean() - y.mean(); t = d / np.sqrt(x.var() / len(x) + y.var() / len(y))
    return f"{x.mean()*1e4:+5.1f} vs {y.mean()*1e4:+5.1f} bp (t={t:+.1f}, n={len(x)})"
PER = [("1950", "1987"), ("1988", "2007"), ("2008", "2026")]
print("periodai: 1950–87 | 1988–2007 | 2008–26")
for nm, m in (("prieššventinė diena", preh), ("algų dienos (1–2, 15–16)", pay), ("pirmadienis", mon)):
    print(f"{nm:26s} " + " | ".join(stat(m, a, b) for a, b in PER))
