"""57: FED grynasis likvidumas (WALCL − TGA − RRP; Twitter/Max Anderson ~2022): laikyti SPY/QQQ/BTC, kai likvidumas auga.
FRED savaitiniai (trečiadienio) duomenys skelbiami ketvirtadienį vakare -> naudojami nuo penktadienio uždarymo (2 d. vėlavimas + 1 d. prekybos).
Mokestis 0,1 % (BTC), 0,02 % (ETF). Paleisti: ../../quantconnect-lean/.venv/bin/python test.py"""
import json, os
import pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(D); ROOT = os.path.dirname(R)
f = lambda s: pd.read_csv(f"{D}/data/{s}.csv", index_col=0, parse_dates=True, na_values=".").iloc[:, 0].astype(float)
walcl, tga, rrp = f("WALCL"), f("WTREGEN"), f("RRPONTSYD")
nl = (walcl - tga - rrp.reindex(walcl.index, method="ffill").fillna(0) * 1000).dropna()
nl.index = nl.index + pd.Timedelta(days=2)                       # žinoma nuo penktadienio
etf = pd.read_csv(f"{ROOT}/etf-rotation/data/close.csv", index_col=0, parse_dates=True)
cm = pd.DataFrame(json.load(open(f"{R}/53_mvrv/data/cm.json"))["data"]); cm["time"] = pd.to_datetime(cm.time).dt.tz_localize(None)
btc = cm[cm.asset == "btc"].set_index("time").PriceUSD.astype(float)
def st(e, a, b):
    e = e[(e.index >= a) & (e.index < b)]
    if len(e) < 100: return "   –"
    e = e / e.iloc[0]; y = (e.index[-1] - e.index[0]).days / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+6.1f}% kr {(e / e.cummax() - 1).min() * 100:4.0f}%"
P = [("2009-01-01", "2016-01-01"), ("2016-01-01", "2023-01-01"), ("2023-01-01", "2027-01-01")]
print("periodai: 2009–15 | 2016–22 | 2023–26 (po išpopuliarinimo)")
for nm, px, fee in (("SPY", etf.SPY.dropna(), 0.0002), ("QQQ", etf.QQQ.dropna(), 0.0002), ("BTC", btc, 0.001)):
    sig_base = nl.reindex(px.index, method="ffill")
    r = px.pct_change().shift(-1).fillna(0)
    def show(lbl, s):
        pos = s.shift(1).fillna(0)
        e = (1 + r * pos - pos.diff().abs().fillna(0) * fee).cumprod()
        print(f"{nm} {lbl:30s} " + " | ".join(st(e, a, b) for a, b in P) + f" | rinkoje {pos.mean()*100:3.0f}%")
    print(); show("laikyti", pd.Series(1.0, px.index))
    for w in (4, 8, 13, 26):
        ch = nl.diff(w).reindex(px.index, method="ffill")
        show(f"likv. pokytis {w} sav. > 0", (ch > 0).astype(float))
    for w in (13, 26):
        ma = nl.rolling(w).mean().reindex(px.index, method="ffill")
        show(f"likv. > {w} sav. vidurkis", (sig_base > ma).astype(float))
    show("kaina > 200 d. SMA (palyg.)", (px > px.rolling(200).mean()).astype(float))
