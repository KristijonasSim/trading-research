"""Ken French momentum decilės (value-weighted, perskaičiuojamos kasdien, be kaštų) vs rinka, pagal laikotarpius."""
import sys
from industry import read_ff, st
d = sys.argv[1]
M = read_ff(f"{d}/10_Portfolios_Prior_12_2_Daily.csv", "Average Value Weighted Returns -- Daily")
F = read_ff(f"{d}/F-F_Research_Data_Factors_daily.csv", "Mkt-RF").reindex(M.index)
mkt = F["Mkt-RF"] + F["RF"]
P = [("1927-01-01", "1999-12-31"), ("2000-01-01", "2014-12-31"), ("2015-01-01", "2026-12-31"), ("2021-01-01", "2026-12-31")]
print(" " * 16 + " | ".join(f"{a[:4]}-{b[:4]}".ljust(19) for a, b in P))
print(f"{'rinka':16}" + " | ".join(st(mkt, a, b).ljust(19) for a, b in P))
for c in ["PRIOR 8", "PRIOR 9", "Hi PRIOR"]:
    print(f"{c:16}" + " | ".join(st(M[c], a, b).ljust(19) for a, b in P))
top2 = (M["PRIOR 9"] + M["Hi PRIOR"]) / 2
print(f"{'top 20 %':16}" + " | ".join(st(top2, a, b).ljust(19) for a, b in P))
y = M["Hi PRIOR"]["2015":].groupby(M["2015":].index.year).apply(lambda x: round(100 * ((1 + x).prod() - 1)))
ym = mkt["2015":].groupby(mkt["2015":].index.year).apply(lambda x: round(100 * ((1 + x).prod() - 1)))
print("Hi PRIOR / rinka pagal metus:", {k: (y[k], ym[k]) for k in y.index})
