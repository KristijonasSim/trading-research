"""Binance USDT-M perpetual: funding istorija ir dienos žvakės visiems (įskaitant išregistruotus) kontraktams.
-> papers/data/funding/<SYM>.csv (t,rate) ir papers/data/perp_1d/<SYM>.csv"""
import json, time, urllib.request, os
from concurrent.futures import ThreadPoolExecutor
D = os.path.dirname(os.path.abspath(__file__)); F = "https://fapi.binance.com/fapi/v1/"
os.makedirs(f"{D}/data/funding", exist_ok=True); os.makedirs(f"{D}/data/perp_1d", exist_ok=True)
def get(u):
    for i in range(5):
        try: return json.load(urllib.request.urlopen(u, timeout=30))
        except Exception: time.sleep(3 + 5 * i)
    return None
info = get(F + "exchangeInfo")
syms = [s["symbol"] for s in info["symbols"] if s["quoteAsset"] == "USDT" and s["contractType"] == "PERPETUAL"]
print(len(syms), flush=True)
def one(sym):
    f = f"{D}/data/funding/{sym}.csv"
    if not os.path.exists(f):
        rows, start = [], 1567296000000
        while True:
            k = get(f"{F}fundingRate?symbol={sym}&limit=1000&startTime={start}")
            if not k: break
            rows += k
            if len(k) < 1000: break
            start = k[-1]["fundingTime"] + 1; time.sleep(0.3)
        open(f, "w").write("t,rate\n" + "".join(f"{r['fundingTime']},{r['fundingRate']}\n" for r in rows))
    f = f"{D}/data/perp_1d/{sym}.csv"
    if not os.path.exists(f):
        rows, start = [], 1567296000000
        while True:
            k = get(f"{F}klines?symbol={sym}&interval=1d&limit=1000&startTime={start}")
            if not k: break
            rows += k
            if len(k) < 1000: break
            start = k[-1][0] + 86400000; time.sleep(0.3)
        open(f, "w").write("t,o,h,l,c,v,qv\n" + "".join(f"{r[0]},{r[1]},{r[2]},{r[3]},{r[4]},{r[5]},{r[7]}\n" for r in rows))
with ThreadPoolExecutor(4) as ex: list(ex.map(one, syms))
print("FUNDING_DONE")
