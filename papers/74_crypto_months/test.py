"""74: Kripto mėnesių sezoniškumas (populiarūs teiginiai: „Uptober“, blogas rugsėjis, stiprus IV ketvirtis, „Sell in May“ kripto).
BTC (Coin Metrics 2011+? – turimi duomenys nuo 2014), ETH nuo 2016. Mėnesio grąžų statistika ir taisyklės: be rugsėjo; tik spalis–gruodis; lapkritis–balandis.
Walk-forward: kiekvienais metais renkami 4 geriausi mėnesiai pagal visą ankstesnę istoriją. Mokestis 0,1 %. Paleisti: quantconnect-lean/.venv/bin/python papers/74_crypto_months/test.py"""
import json, os
import numpy as np, pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(D)
cm = pd.DataFrame(json.load(open(f"{R}/53_mvrv/data/cm.json"))["data"]); cm["time"] = pd.to_datetime(cm.time).dt.tz_localize(None)
for a in ("btc", "eth"):
    p = cm[cm.asset == a].set_index("time").PriceUSD.astype(float).dropna(); m = p.resample("ME").last().pct_change().dropna()
    tab = m.groupby(m.index.month).agg(["mean", "median", lambda x: (x > 0).mean(), "count"]); tab.columns = ["vid", "med", "teig", "n"]
    print(f"\n== {a.upper()} {m.index[0].year}–{m.index[-1].year} mėnesių grąžos (%) ==")
    print(" ".join(f"{k:>2}:{v.vid*100:+5.1f}/{v.teig*100:3.0f}%" for k, v in tab.iterrows()))
    # taisyklės (mėnesio lygiu, mokestis už įėjimą/išėjimą)
    def run(mask, nm):
        pos = pd.Series(mask, m.index).astype(float); x = pos * m - pos.diff().abs().fillna(pos.iloc[0]) * 0.001
        e = (1 + x).cumprod(); y = len(x) / 12; first = x["2014":"2019"]; last = x["2020":]
        cg = lambda z: ((1 + z).prod() ** (12 / len(z)) - 1) * 100
        print(f"  {nm:34s} visas {(e.iloc[-1] ** (1 / y) - 1) * 100:+6.1f}%/m. kr {(e / e.cummax() - 1).min() * 100:4.0f}% | iki 2019 {cg(first):+6.1f} | 2020–26 {cg(last):+6.1f} | rinkoje {pos.mean()*100:.0f}%")
    run(np.ones(len(m)), "laikyti")
    run(m.index.month != 9, "be rugsėjo")
    run(m.index.month.isin([10, 11, 12]), "tik spalis–gruodis")
    run(m.index.month.isin([11, 12, 1, 2, 3, 4]), "lapkritis–balandis")
    # walk-forward: 4 geriausi mėnesiai pagal praeitį (min 3 m. istorijos)
    wf = []
    for t in m.index:
        past = m[m.index < pd.Timestamp(t.year, 1, 1)]
        if past.index.year.nunique() < 3: wf.append(1.0); continue
        best = past.groupby(past.index.month).mean().nlargest(6).index; wf.append(float(t.month in best))
    run(np.array(wf), "walk-forward 6 geriausi mėn.")
