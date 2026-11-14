"""65 patikra: be vienos monetos (leave-one-out), 1 sav. papildomas vėlavimas, mokestis 0,3 %, top 1/3 vs lygiai, metai."""
import json, os
import numpy as np, pandas as pd
D = os.path.dirname(os.path.abspath(__file__))
d = pd.DataFrame(json.load(open(f"{D}/data/adr.json"))); d["time"] = pd.to_datetime(d.time).dt.tz_localize(None)
A = d.pivot(index="time", columns="asset", values="AdrActCnt").astype(float); P = d.pivot(index="time", columns="asset", values="PriceUSD").astype(float)
R1 = P.pct_change(fill_method=None)
def run(cols, lb=7, lag=0, fee=0.001, sgn=1):
    S = np.log(A[cols].rolling(7).mean()).diff(lb).shift(lag); eq, dates, wprev = [1.0], [P.index[0]], pd.Series(0.0, cols)
    for i in range(200, len(P) - 1, 7):
        ok = S.iloc[i].dropna().index.intersection(P[cols].iloc[i].dropna().index)
        if len(ok) < 7: continue
        k = max(1, len(ok) // 3); w = pd.Series(0.0, cols)
        if sgn == 0: w[ok] = 1 / len(ok)
        else: w[(sgn * S.iloc[i][ok]).nlargest(k).index] = 1 / k
        cost = (w - wprev).abs().sum() * fee; j = min(i + 7, len(P) - 1)
        rr = R1.iloc[i + 1:j + 1][w[w > 0].index].fillna(0); val = ((1 + rr).cumprod() * w[w > 0]).sum(axis=1)
        e0 = eq[-1] * (1 - cost); eq += list(e0 * val.values); dates += list(rr.index); wprev = w
    return pd.Series(eq, dates)
def cg(e, a, b):
    e = e[(e.index >= a) & (e.index < b)]; y = (e.index[-1] - e.index[0]).days / 365.25; return (e.iloc[-1] / e.iloc[0]) ** (1 / y) * 100 - 100
PER = [("2017-01-01", "2020-01-01"), ("2020-01-01", "2023-01-01"), ("2023-01-01", "2027-01-01")]
allc = list(A.columns)
def line(nm, e, eb):
    print(f"{nm:28s} top: " + " | ".join(f"{cg(e,a,b):+6.1f}" for a, b in PER) + "   top − lygiai: " + " | ".join(f"{cg(e,a,b)-cg(eb,a,b):+6.1f}" for a, b in PER))
eb = run(allc, sgn=0)
line("bazė 7 d.", run(allc), eb)
line("bazė 7 d., +7 d. vėlavimas", run(allc, lag=7), eb)
line("bazė 7 d., mokestis 0,3 %", run(allc, fee=0.003), run(allc, sgn=0, fee=0.003))
line("14 d.", run(allc, lb=14), eb)
for c in allc:
    cols = [x for x in allc if x != c]; line(f"be {c}", run(cols), run(cols, sgn=0))
e = run(allc); yr = e.resample("YE").last().pct_change(); yb = eb.resample("YE").last().pct_change()
print("metai top / lygiai:", {k.year: f"{v*100:+.0f}/{yb[k]*100:+.0f}" for k, v in yr.dropna().items()})
dd = (e["2023":] / e["2023":].cummax() - 1).min(); print(f"kritimas 2023–26 {dd*100:.0f}%")
