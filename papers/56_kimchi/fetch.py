"""Upbit KRW-BTC, KRW-ETH, KRW-USDT dienos žvakės (viešas API, 200/užklausa)."""
import json, time, urllib.request, os, datetime as dt
D = os.path.dirname(os.path.abspath(__file__))
for m in ("KRW-BTC", "KRW-ETH", "KRW-USDT", "KRW-XRP"):
    rows, to = {}, None
    while True:
        u = f"https://api.upbit.com/v1/candles/days?market={m}&count=200" + (f"&to={to}" if to else "")
        k = None
        for i in range(5):
            try: k = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "research-script"}), timeout=30)); break
            except Exception: time.sleep(2 + 3 * i)
        if not k: break
        for r in k: rows[r["candle_date_time_utc"][:10]] = r["trade_price"]
        to = k[-1]["candle_date_time_utc"] + "Z"
        if len(k) < 200: break
        time.sleep(0.15)
    json.dump(rows, open(f"{D}/data/{m}.json", "w")); print(m, len(rows), min(rows), flush=True)
