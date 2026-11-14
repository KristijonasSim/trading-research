"""67: Dėmesio signalas (Kristoufek 2013 „BitCoin meets Google Trends and Wikipedia“; Urquhart 2018): Wikipedia peržiūrų pokytis ir BTC/ETH grąža.
Kristoufek: peržiūroms augant kylant kainai – burbulo stiprinimas, krentant – panika. Taisyklės: A) peržiūros 7 d. vid. > 28/90 d. vid. ir kaina > 7 d. prieš -> laikyti;
B) peržiūrų šuolis (z > 2) -> grynieji (euforija/panika); C) tik peržiūrų trendas. Wikimedia API (user agent), 1 d. vėlavimas, 0,1 % mokestis.
Paleisti: quantconnect-lean/.venv/bin/python papers/67_wiki_attention/test.py"""
import json, os
import pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(D); FEE = 0.001
def wv(a):
    it = json.load(open(f"{D}/data/{a}.json"))["items"]; return pd.Series({pd.to_datetime(x["timestamp"][:8]): x["views"] for x in it})
cm = pd.DataFrame(json.load(open(f"{R}/53_mvrv/data/cm.json"))["data"]); cm["time"] = pd.to_datetime(cm.time).dt.tz_localize(None)
def st(e, a, b):
    e = e[(e.index >= a) & (e.index < b)].dropna(); e = e / e.iloc[0]; y = (e.index[-1] - e.index[0]).days / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+6.1f}% kr {(e / e.cummax() - 1).min() * 100:4.0f}%"
PER = [("2016-01-01", "2020-01-01"), ("2020-01-01", "2023-01-01"), ("2023-01-01", "2027-01-01")]
print("periodai: 2016–19 | 2020–22 | 2023–26")
for c, art in (("btc", "Bitcoin"), ("eth", "Ethereum")):
    p = cm[cm.asset == c].set_index("time").PriceUSD.astype(float); v = wv(art).reindex(p.index)
    p = p[v.notna()]; v = v[v.notna()]; r = p.pct_change().shift(-1).fillna(0)
    def show(nm, pos):
        pos = pos.fillna(0); e = (1 + r * pos - pos.diff().abs().fillna(0) * FEE).cumprod()
        print(f"{c.upper()} {nm:40s} " + " | ".join(st(e, a, b) for a, b in PER) + f" | rinkoje {pos.mean()*100:3.0f}%")
    print(); show("laikyti", pd.Series(1.0, p.index))
    v7 = v.rolling(7).mean(); up = p > p.shift(7)
    for l in (28, 90):
        show(f"A peržiūros 7d > {l}d ir kaina ↑ 7 d.", ((v7 > v.rolling(l).mean()) & up).astype(float))
        show(f"C peržiūros 7d > {l}d", (v7 > v.rolling(l).mean()).astype(float))
        show(f"C peržiūros 7d < {l}d (atvirkščiai)", (v7 < v.rolling(l).mean()).astype(float))
    lv = v.rolling(90).mean(); z = (v7 - lv) / v.rolling(90).std()
    for k in (1.5, 2.0):
        show(f"B grynieji kai peržiūrų z(90) > {k}", (z <= k).astype(float))
    show("palyg.: kaina > 100 d. SMA", (p > p.rolling(100).mean()).astype(float))
    show("palyg.: tik kaina ↑ 7 d. (be peržiūrų)", up.astype(float))
    show("palyg.: kaina ↑ 7 d. ir > 28 d. vid. kainos", (up & (p > p.rolling(28).mean())).astype(float))
