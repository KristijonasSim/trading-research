"""Coinbase BTC-USD ir ETH-USD valandinės žvakės 2019-01 – dabar (viešas API, 300 žvakių/užklausa)."""
import json, time, urllib.request, os, datetime as dt
D = os.path.dirname(os.path.abspath(__file__))
for prod in ("BTC-USD", "ETH-USD"):
    rows, t = {}, dt.datetime(2019, 1, 1)
    end = dt.datetime.utcnow()
    while t < end:
        t2 = t + dt.timedelta(hours=300)
        u = f"https://api.exchange.coinbase.com/products/{prod}/candles?granularity=3600&start={t.isoformat()}&end={t2.isoformat()}"
        for i in range(5):
            try:
                req = urllib.request.Request(u, headers={"User-Agent": "research-script"})
                k = json.load(urllib.request.urlopen(req, timeout=30)); break
            except Exception: time.sleep(3 + 3 * i); k = []
        for r in k: rows[r[0]] = r
        t = t2; time.sleep(0.35)
    json.dump(sorted(rows.values()), open(f"{D}/data/{prod}.json", "w"))
    print(prod, len(rows), flush=True)
print("FETCH_DONE")
