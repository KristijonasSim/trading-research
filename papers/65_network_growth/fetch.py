"""Coin Metrics community: AdrActCnt ir PriceUSD, 1d, 2015 – dabar (su puslapiavimu)."""
import json, os, urllib.request, time
D = os.path.dirname(os.path.abspath(__file__)); rows = []
for a in "btc eth ltc bch doge xrp ada link etc dash zec xlm trx bnb xmr".split():
    u = f"https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets={a}&metrics=AdrActCnt,PriceUSD&frequency=1d&start_time=2015-01-01&page_size=10000"
    n = 0
    while u:
        d = json.load(urllib.request.urlopen(u, timeout=60))
        if "error" in d: print(a, d["error"]["message"][:80]); break
        rows += d["data"]; n += len(d["data"]); u = d.get("next_page_url"); time.sleep(0.3)
    print(a, n, flush=True)
json.dump(rows, open(f"{D}/data/adr.json", "w"))
