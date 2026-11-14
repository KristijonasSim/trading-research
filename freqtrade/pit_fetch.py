"""Point-in-time duomenys: 2021-11 top 20 monetos, kurių nėra user_data (SHIB, UNI, ALGO, BCH, ATOM, FTT, MATIC, LUNA iki 2022-05-13).
Binance spot klines -> freqtrade feather (date, open, high, low, close, volume) į pitdata/binance/. Paleisti: .venv/bin/python pit_fetch.py"""
import json, time, urllib.request, os
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pitdata/binance")
START, END = int(pd.Timestamp("2021-09-01", tz="UTC").timestamp() * 1000), int(pd.Timestamp("2026-11-09", tz="UTC").timestamp() * 1000)
MS = {"5m": 300000, "15m": 900000, "1h": 3600000}
def get(u):
    for i in range(6):
        try: return json.load(urllib.request.urlopen(u, timeout=30))
        except Exception: time.sleep(2 + 3 * i)
def one(arg):
    c, tf = arg; f = f"{D}/{c}_USDT-{tf}.feather"
    if os.path.exists(f): return
    rows, st = [], START
    while st < END:
        k = get(f"https://api.binance.com/api/v3/klines?symbol={c}USDT&interval={tf}&limit=1000&startTime={st}")
        if not k: break
        rows += k; st = k[-1][0] + MS[tf]
        if len(k) < 1000: break
        time.sleep(0.1)
    d = pd.DataFrame([r[:6] for r in rows], columns=["date", "open", "high", "low", "close", "volume"]).astype(float)
    d["date"] = pd.to_datetime(d.date.astype("int64"), unit="ms", utc=True)
    if c == "LUNA": d = d[d.date < "2022-05-13 12:00"]                 # senoji LUNA; vėliau – kita moneta
    d = d[d.date < pd.Timestamp(END, unit="ms", tz="UTC")].drop_duplicates("date").reset_index(drop=True)
    d.to_feather(f); print(c, tf, len(d), d.date.iloc[0].date(), d.date.iloc[-1].date(), flush=True)
jobs = [(c, tf) for c in "SHIB UNI ALGO BCH ATOM FTT MATIC LUNA".split() for tf in ("5m", "15m", "1h")]
with ThreadPoolExecutor(4) as ex: list(ex.map(one, jobs))
print("PIT_DONE")
