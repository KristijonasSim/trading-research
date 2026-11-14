"""88: BTC ↔ auksas momentum rotacija (populiari „digital gold“ / dual momentum versija): kas mėnesį laikyti BTC arba GLD – kurio 1/3/6 mėn. grąža didesnė,
jei abiejų < 0 – BIL. Palyginimas: 50/50 BTC/GLD kas mėnesį perbalansuojant, BTC laikymas. Mokestis 0,1 % (BTC), 0,03 % (GLD).
Coin Metrics BTC, Yahoo GLD/BIL (savaitgaliai ignoruojami – mėnesio pabaigos kainos). Paleisti: quantconnect-lean/.venv/bin/python papers/88_btc_gold_rotation/test.py"""
import json, os
import pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(D)
cm = pd.DataFrame(json.load(open(f"{R}/53_mvrv/data/cm.json"))["data"]); cm["time"] = pd.to_datetime(cm.time).dt.tz_localize(None)
btc = cm[cm.asset == "btc"].set_index("time").PriceUSD.astype(float)
L = lambda t: pd.read_csv(f"{R}/59_ibs/data/{t}.csv", index_col=0, parse_dates=True).Close
M = pd.DataFrame({"BTC": btc.resample("ME").last(), "GLD": L("GLD").resample("ME").last(), "BIL": L("BIL").resample("ME").last()}).dropna()
RM = M.pct_change(); FEE = {"BTC": 0.001, "GLD": 0.0003, "BIL": 0}
def st(x, a, b):
    x = x[a:b].dropna(); e = (1 + x).cumprod(); n = len(x) / 12; return f"{(e.iloc[-1] ** (1 / n) - 1) * 100:+6.1f}% kr {(e / e.cummax() - 1).min() * 100:3.0f}%"
PER = [("2015", "2019"), ("2020", "2022"), ("2023", "2026")]
print("periodai: 2015–19 | 2020–22 | 2023–26")
print(f"{'BTC laikyti':26s} " + " | ".join(st(RM.BTC, a, b) for a, b in PER))
print(f"{'GLD laikyti':26s} " + " | ".join(st(RM.GLD, a, b) for a, b in PER))
print(f"{'50/50 BTC/GLD':26s} " + " | ".join(st(0.5 * RM.BTC + 0.5 * RM.GLD, a, b) for a, b in PER))
for n in (1, 3, 6):
    mom = M.pct_change(n); out, prev = [], None
    for i in range(6, len(M) - 1):
        s = mom.iloc[i][["BTC", "GLD"]]; best = s.idxmax(); pick = best if s[best] > 0 else "BIL"
        c = (FEE.get(prev, 0) + FEE[pick]) if pick != prev else 0; out.append(RM.iloc[i + 1][pick] - c); prev = pick
    print(f"{'rotacija ' + str(n) + ' mėn.':26s} " + " | ".join(st(pd.Series(out, M.index[7:]), a, b) for a, b in PER))
print("\njautrumas ir palyginimas be aukso (BTC arba BIL pagal absoliutų momentum):")
for n in (1, 2, 3, 4, 5, 6, 9, 12):
    mom = M.pct_change(n)
    for gold in (True, False):
        out, prev = [], None
        for i in range(12, len(M) - 1):
            s = mom.iloc[i][["BTC", "GLD"] if gold else ["BTC"]]; best = s.idxmax(); pick = best if s[best] > 0 else "BIL"
            c = (FEE.get(prev, 0) + FEE[pick]) if pick != prev else 0; out.append(RM.iloc[i + 1][pick] - c); prev = pick
        print(f"  {n:2d} mėn. {'BTC/GLD/BIL' if gold else 'BTC/BIL    '}  " + " | ".join(st(pd.Series(out, M.index[13:]), a, b) for a, b in PER))
