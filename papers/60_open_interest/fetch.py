"""Bybit USDT perp dienos atvirų pozicijų (OI, monetomis) istorija 2020-06 – dabar, 30 didelių monetų."""
import json, time, urllib.request, os
D = os.path.dirname(os.path.abspath(__file__))
C = "BTC ETH XRP BNB SOL DOGE ADA TRX LINK AVAX LTC DOT BCH ETC XLM ATOM FIL UNI NEAR AAVE EOS XTZ ALGO SAND MANA AXS MATIC FTM THETA EGLD".split()
for c in C:
    rows, st, end = {}, 1590969600000, int(time.time() * 1000)
    while st < end:
        u = f"https://api.bybit.com/v5/market/open-interest?category=linear&symbol={c}USDT&intervalTime=1d&limit=200&startTime={st}&endTime={st + 199 * 86400000}"
        try: k = json.load(urllib.request.urlopen(u, timeout=30))["result"]["list"]
        except Exception: time.sleep(3); continue
        for r in k: rows[int(r["timestamp"])] = float(r["openInterest"])
        st += 200 * 86400000; time.sleep(0.12)
    json.dump(rows, open(f"{D}/data/{c}.json", "w")); print(c, len(rows), flush=True)
