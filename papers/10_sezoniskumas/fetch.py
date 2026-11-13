"""BTC/ETH ir dar 8 senų monetų 1h žvakės nuo 2017-08 (Binance spot)."""
import json, time, urllib.request, sys
import pandas as pd
def get(u):
    for i in range(5):
        try: return json.load(urllib.request.urlopen(u, timeout=30))
        except Exception: time.sleep(2 + 3 * i)
for s in ["BTCUSDT", "ETHUSDT", "BNBUSDT", "LTCUSDT", "XRPUSDT", "ADAUSDT", "TRXUSDT", "LINKUSDT"]:
    rows, start = [], 1501545600000
    while True:
        k = get(f"https://api.binance.com/api/v3/klines?symbol={s}&interval=1h&limit=1000&startTime={start}")
        if not k: break
        rows += k
        if len(k) < 1000: break
        start = k[-1][0] + 3600000
    df = pd.DataFrame([(r[0], float(r[1]), float(r[4])) for r in rows], columns=["t", "o", "c"])
    df["t"] = pd.to_datetime(df.t, unit="ms"); df.to_pickle(f"data/{s}.pkl"); print(s, len(df), df.t.iloc[0], flush=True)
