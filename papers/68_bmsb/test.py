"""68: Bull Market Support Band (20 sav. SMA + 21 sav. EMA; populiarus BTC kanaluose ~2019+). Laikyti, kai savaitės uždarymas > abiejų (arba > žemesnės),
parduoti kai savaitės uždarymas < abiejų. Savaitinis signalas sekmadienio uždarymu, prekyba pirmadienį. Mokestis 0,1 %. BTC, ETH, alts10 (lygiais svoriais, kiekviena atskirai).
Duomenys papers/data/binance_1d (2017-08+), BTC 2014+ iš Coin Metrics. Paleisti: quantconnect-lean/.venv/bin/python papers/68_bmsb/test.py"""
import json, os
import numpy as np, pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(D); FEE = 0.001
def load(c):
    b = pd.read_csv(f"{R}/data/binance_1d/{c}USDT.csv"); return pd.Series(b.c.values, pd.to_datetime(b.t, unit="ms"))
cm = pd.DataFrame(json.load(open(f"{R}/53_mvrv/data/cm.json"))["data"]); cm["time"] = pd.to_datetime(cm.time).dt.tz_localize(None)
def st(e, a, b):
    e = e[(e.index >= a) & (e.index < b)].dropna()
    if len(e) < 100: return "     –"
    e = e / e.iloc[0]; y = (e.index[-1] - e.index[0]).days / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+6.1f}% kr {(e / e.cummax() - 1).min() * 100:4.0f}%"
PER = [("2015-01-01", "2019-01-01"), ("2019-01-01", "2022-01-01"), ("2022-01-01", "2027-01-01")]
def strat(px, mode):
    w = px.resample("W-SUN").last(); sma = w.rolling(20).mean(); ema = w.ewm(span=21, adjust=False).mean()
    if mode == "abu": sig = pd.Series(np.nan, w.index); sig[(w > sma) & (w > ema)] = 1; sig[(w < sma) & (w < ema)] = 0; sig = sig.ffill().fillna(0)
    elif mode == "sma": sig = (w > sma).astype(float)
    pos = sig.reindex(px.index, method="ffill").shift(1).fillna(0)      # nuo pirmadienio
    r = px.pct_change().fillna(0); return (1 + pos * r - pos.diff().abs().fillna(0) * FEE).cumprod(), pos
print("periodai: 2015–18 | 2019–21 | 2022–26")
assets = {"BTC (CM)": cm[cm.asset == "btc"].set_index("time").PriceUSD.astype(float), "ETH": load("ETH")}
for c in "XRP BNB SOL DOGE ADA TRX LINK AVAX LTC DOT".split(): assets[c] = load(c)
rows = {}
for nm, px in assets.items():
    px = px[px.index >= "2014-06-01"]
    e0 = px / px.iloc[0]; e1, p1 = strat(px, "abu"); e2, _ = strat(px, "sma")
    print(f"{nm:9s} laikyti {' | '.join(st(e0, a, b) for a, b in PER)}\n{'':9s} BMSB    {' | '.join(st(e1, a, b) for a, b in PER)} | rinkoje {p1.mean()*100:.0f}%\n{'':9s} 20sSMA  {' | '.join(st(e2, a, b) for a, b in PER)}")
    rows[nm] = e1.pct_change()
alts = pd.DataFrame({k: v for k, v in rows.items() if k not in ("BTC (CM)", "ETH")}).fillna(0).mean(axis=1)
print(f"alts10 BMSB krepšelis (kasdien lygiai): {' | '.join(st((1 + alts).cumprod(), a, b) for a, b in PER)}")
