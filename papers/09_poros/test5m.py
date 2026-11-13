"""Tas pats porų testas 5 min. rėme (freqtrade duomenys, 12 monetų, 2021-11 – 2026-11)."""
import sys, itertools, numpy as np, pandas as pd
D = "../../freqtrade/user_data/data/binance/"
SY = ["BTC", "ETH", "XRP", "BNB", "SOL", "DOGE", "ADA", "TRX", "LINK", "AVAX", "LTC", "DOT"]
P = pd.concat({s: pd.read_feather(f"{D}{s}_USDT-5m.feather").set_index("date").close for s in SY}, axis=1).ffill().dropna()
src = open("test.py").read().split("rows = []; yearly")[0].split("PAIRS = ")[1]
L = np.log(P); R = P.pct_change().fillna(0)
exec("PAIRS = " + src)
rows = []
for m in ["dist", "coint"]:
    for fd in [3, 10]:
        for fee in [0.0, 0.0002, 0.0005, 0.001]:
            r = run(m, fd * 288, 5, 2.0, fee, step=288)
            yr = ((1 + r).groupby(r.index.year).prod() - 1).mul(100).round(1).to_dict()
            rows.append((m, fd, fee * 100, *st(r), yr)); print(rows[-1], flush=True)
open("REZULTATAI_5m.txt", "w").write(pd.DataFrame(rows, columns=["metodas", "formavimas d.", "mokestis %", "%/m", "kritimas", "metai"]).to_markdown(index=False) + "\n")
