"""121: Tom Hougaard „ketvirtadienio taisyklė“ (Instagram tailwindtrades, 2026-10-29): jei trečiadienis užsidaro žemiau
pirmadienio aukščiausios kainos, ketvirtadienį kaina nukrenta žemiau trečiadienio žemiausios (24 iš 25).
Tikrinama: tikimybė su sąlyga ir be jos; prekyba – short trečiadienio uždarymu, išėjimas ketv. uždarymu
arba tikslas = treč. žemiausia, stop = treč. aukščiausia (jei abu tą pačią dieną – laikomas stop). Mokestis 0,02 % (indeksai), 0,1 % (kripto)."""
import json, os, pandas as pd, numpy as np
D = os.path.dirname(os.path.abspath(__file__))
def yahoo(s):
    d = json.load(open(f"{D}/data/{s}.json"))["chart"]["result"][0]; q = d["indicators"]["quote"][0]
    return pd.DataFrame({k: q[k] for k in ("open", "high", "low", "close")}, index=pd.to_datetime(d["timestamp"], unit="s").normalize()).dropna()
def binance(s):
    d = pd.read_csv(f"{D}/../data/binance_1d/{s}USDT.csv"); return pd.DataFrame({"open": d.o.values, "high": d.h.values, "low": d.l.values, "close": d.c.values}, index=pd.to_datetime(d.t, unit="ms"))
def weeks(df):
    rows = []
    for _, g in df.groupby(df.index.to_period("W-SUN")):
        dw = {d.dayofweek: r for d, r in g.iterrows()}
        if 0 in dw and 2 in dw and 3 in dw: rows.append((g.index[0], dw[0], dw[2], dw[3]))
    return rows
def analyse(name, df, fee, periods):
    out = []
    for a, b in periods:
        W = [w for w in weeks(df[(df.index >= a) & (df.index < b)])]
        if len(W) < 30: continue
        cond = [w for w in W if w[2].close < w[1].high]; notc = [w for w in W if w[2].close >= w[1].high]
        p = lambda S: np.mean([w[3].low < w[2].low for w in S]) * 100 if S else float("nan")
        # prekyba
        r1 = np.array([-(w[3].close / w[2].close - 1) - fee for w in cond])
        r2 = []
        for w in cond:
            ent, tgt, stp = w[2].close, w[2].low, w[2].high
            if w[3].high >= stp: r2.append(-(stp / ent - 1) - fee)
            elif w[3].low <= tgt: r2.append((ent - tgt) / ent - fee)
            else: r2.append(-(w[3].close / ent - 1) - fee)
        r2 = np.array(r2); rand = np.array([-(w[3].close / w[2].close - 1) - fee for w in W])
        yrs = (pd.Timestamp(b) - pd.Timestamp(a)).days / 365.25
        cg = lambda r: ((1 + r).prod() ** (1 / yrs) - 1) * 100
        out.append(f"| {name} | {a[:4]}–{b[:4]} | {len(W)} | {len(cond)} | **{p(cond):.0f} %** | {p(notc):.0f} % | {p(W):.0f} % | {r1.mean()*100:+.3f} % ({cg(r1):+.1f} %/m.) | {r2.mean()*100:+.3f} % ({cg(r2):+.1f} %/m., laimi {np.mean(r2>0)*100:.0f} %) | {rand.mean()*100:+.3f} % |")
    return out
P0 = [("1992-01-01", "2010-01-01"), ("2010-01-01", "2020-01-01"), ("2020-01-01", "2026-11-17"), ("1992-01-01", "2026-11-17")]
out = ["# 121 Hougaard ketvirtadienio taisyklė – rezultatai\n",
       "| Rinka | Laikotarpis | Savaičių | Su sąlyga | Ketv. < treč. žemiausios (su sąlyga) | (be sąlygos: treč. > pirm. aukšč.) | (visos savaitės) | Short treč.→ketv. uždarymas, vid. | Short su tikslu/stop, vid. | Short visada (palyginimui) |",
       "|---|---|---|---|---|---|---|---|---|---|"]
for n, s in [("Dow Jones", "DJI"), ("S&P 500", "GSPC"), ("Nasdaq-100", "NDX")]: out += analyse(n, yahoo(s), 0.0002, P0)
for n, s in [("BTC", "BTC"), ("ETH", "ETH")]: out += analyse(n, binance(s), 0.001, [("2018-01-01", "2022-01-01"), ("2022-01-01", "2026-11-17")])
open(f"{D}/rezultatai_raw.md", "w").write("\n".join(out) + "\n"); print("\n".join(out))
