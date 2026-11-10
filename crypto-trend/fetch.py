"""Binance spot dienos žvakės visoms USDT poroms (ir iš biržos išimtoms, status BREAK) nuo 2017-08 -> <out>/<SYMBOL>.csv"""
import json, sys, time, urllib.request
from pathlib import Path
import pandas as pd
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
info = json.load(urllib.request.urlopen("https://api.binance.com/api/v3/exchangeInfo?permissions=SPOT", timeout=60))
syms = [s["symbol"] for s in info["symbols"] if s["quoteAsset"] == "USDT"]
K, N = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (0, 1)
syms = syms[K::N]
for sym in syms:
    f = out / f"{sym}.csv"
    if f.exists():
        continue
    rows, start = [], 1502928000000  # 2017-08-17
    while True:
        u = f"https://api.binance.com/api/v3/klines?symbol={sym}&interval=1d&startTime={start}&limit=1000"
        for k in range(5):
            try:
                r = json.load(urllib.request.urlopen(u, timeout=60)); break
            except Exception as e:
                time.sleep(5 * (k + 1)); r = None
        if not r:
            break
        rows += r
        if len(r) < 1000:
            break
        start = r[-1][0] + 86400000
        time.sleep(0.15)
    if rows:
        df = pd.DataFrame(rows, columns=["t", "open", "high", "low", "close", "vol", "ct", "qvol", "n", "tb", "tq", "x"])
        df["date"] = pd.to_datetime(df.t, unit="ms")
        df[["date", "open", "high", "low", "close", "qvol"]].to_csv(f, index=False)
    time.sleep(0.15)
print("DONE", len(list(out.glob("*.csv"))))
