"""Visų Binance spot USDT porų (ir išregistruotų, status BREAK) dienos žvakės 2017-08 – dabar.
Išregistruotos monetos įtraukiamos, kad nebūtų išgyvenusiųjų iškraipymo.
Paleisti: python3 papers/fetch_binance_1d.py  -> papers/data/binance_1d/<SYMBOL>.csv"""
import json, time, urllib.request, os, sys
from concurrent.futures import ThreadPoolExecutor
OUT = os.path.join(os.path.dirname(__file__), "data/binance_1d")
B = "https://api.binance.com/api/v3/"
STABLE = {"USDC","BUSD","TUSD","PAX","USDP","FDUSD","DAI","USDS","EUR","GBP","AUD","USTC","UST","SUSD","EURI","AEUR","XUSD","USD1","BFUSD","RLUSD","PAXG","WBTC","WBETH","BKRW","BIDR","IDRT","BVND","TRY","BRL","RUB","ZAR","UAH","NGN"}
def get(u):
    for i in range(5):
        try: return json.load(urllib.request.urlopen(u, timeout=30))
        except Exception as e: time.sleep(2 + 3*i)
    return None
info = get(B + "exchangeInfo")
syms = [s["symbol"] for s in info["symbols"] if s["quoteAsset"] == "USDT" and s["baseAsset"] not in STABLE
        and not any(x in s["baseAsset"] for x in ("UP", "DOWN", "BULL", "BEAR")) or (s["quoteAsset"]=="USDT" and s["baseAsset"] in ("JUP","SUPER","UPC"))]
print(len(syms), "simbolių", flush=True)
def one(sym):
    f = os.path.join(OUT, sym + ".csv")
    if os.path.exists(f): return
    rows, start = [], 1501545600000
    while True:
        k = get(f"{B}klines?symbol={sym}&interval=1d&limit=1000&startTime={start}")
        if not k: break
        rows += k
        if len(k) < 1000: break
        start = k[-1][0] + 86400000
        time.sleep(0.2)
    with open(f, "w") as fh:
        fh.write("t,o,h,l,c,v,qv\n")
        for r in rows: fh.write(f"{r[0]},{r[1]},{r[2]},{r[3]},{r[4]},{r[5]},{r[7]}\n")
with ThreadPoolExecutor(6) as ex: list(ex.map(one, syms))
print("FETCH_DONE")
