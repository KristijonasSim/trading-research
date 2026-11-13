"""Pelno anonsų datos ir EPS staigmena (Yahoo) visoms akcijoms, kurios turi kainas ../07_lowvol/data/closes.pkl."""
import pandas as pd, yfinance as yf, time, os, pickle
C = pd.read_pickle("../07_lowvol/data/closes.pkl")
T = [c for c in C.columns if c not in ("SPY", "SPLV", "USMV")]
f = "data/earn.pkl"
D = pickle.load(open(f, "rb")) if os.path.exists(f) else {}
for i, t in enumerate(T):
    if t in D: continue
    for a in range(3):
        try:
            e = yf.Ticker(t).get_earnings_dates(limit=100)
            D[t] = e if e is not None else pd.DataFrame(); break
        except Exception as ex:
            msg = str(ex)
            if "Rate" in msg or "Too Many" in msg: time.sleep(60)
            else: D[t] = pd.DataFrame(); break
    time.sleep(0.7)
    if i % 50 == 0:
        pickle.dump(D, open(f, "wb")); print(i, len(T), sum(len(v) > 0 for v in D.values()), flush=True)
pickle.dump(D, open(f, "wb")); print("DONE", sum(len(v) > 0 for v in D.values()))
