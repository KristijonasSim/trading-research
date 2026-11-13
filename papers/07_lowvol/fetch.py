import pandas as pd, yfinance as yf
H = pd.read_csv("data/hist.csv")
t = sorted({x for s in H.tickers for x in s.split(",")}) + ["SPY", "SPLV", "USMV"]
t = [x.replace(".", "-") for x in t]
d = yf.download(t, start="1999-01-01", end="2026-11-13", auto_adjust=True, progress=False, threads=True)["Close"]
d = d.dropna(axis=1, how="all"); d.to_pickle("data/closes.pkl"); print(len(t), d.shape)
