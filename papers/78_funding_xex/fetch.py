"""Bybit USDT perp funding istorija (8 h) 2020 – dabar."""
import json, time, urllib.request, os
D = os.path.dirname(os.path.abspath(__file__))
for c in "BTC ETH XRP BNB SOL DOGE ADA TRX LINK AVAX LTC DOT".split():
    rows, end = {}, int(time.time() * 1000)
    while True:
        u = f"https://api.bybit.com/v5/market/funding/history?category=linear&symbol={c}USDT&limit=200&endTime={end}"
        try: k = json.load(urllib.request.urlopen(u, timeout=30))["result"]["list"]
        except Exception: time.sleep(3); continue
        if not k: break
        for r in k: rows[int(r["fundingRateTimestamp"])] = float(r["fundingRate"])
        new_end = min(int(r["fundingRateTimestamp"]) for r in k) - 1
        if new_end >= end or len(k) < 200: break
        end = new_end; time.sleep(0.1)
    json.dump(rows, open(f"{D}/data/{c}.json", "w")); print(c, len(rows), time.strftime("%Y-%m-%d", time.gmtime(min(rows) / 1000)), flush=True)
