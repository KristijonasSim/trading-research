"""Binance spot USDT porų dienos žvakės su taker buy apimtimi (kline[9] base, [10] quote). Simboliai – tie patys kaip papers/data/binance_1d."""
import json, time, urllib.request, os, glob
from concurrent.futures import ThreadPoolExecutor
D = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(D)
syms = [os.path.basename(f)[:-4] for f in glob.glob(f"{R}/data/binance_1d/*.csv")]
def get(u):
    for i in range(5):
        try: return json.load(urllib.request.urlopen(u, timeout=30))
        except Exception: time.sleep(2 + 3 * i)
def one(s):
    f = f"{D}/data/{s}.csv"
    if os.path.exists(f): return
    rows, start = [], 1501545600000
    while True:
        k = get(f"https://api.binance.com/api/v3/klines?symbol={s}&interval=1d&limit=1000&startTime={start}")
        if not k: break
        rows += k
        if len(k) < 1000: break
        start = k[-1][0] + 86400000; time.sleep(0.2)
    with open(f, "w") as fh:
        fh.write("t,c,qv,tbqv,n\n")
        for r in rows: fh.write(f"{r[0]},{r[4]},{r[7]},{r[10]},{r[8]}\n")
with ThreadPoolExecutor(6) as ex: list(ex.map(one, syms))
print("FETCH_DONE", len(glob.glob(f"{D}/data/*.csv")))
