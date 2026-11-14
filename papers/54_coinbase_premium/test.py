"""54: Coinbase premija (populiarus teiginys: kai Coinbase BTC-USD brangesnis už Binance BTCUSDT, JAV pirkėjai stumia kainą aukštyn).
premija = CB uždarymas / Binance uždarymas − 1; pakoreguota = premija − 7 d. slenkanti mediana (pašalina USDT/USD kursą).
Signalas valandos t uždaryme, pozicija Binance BTC/ETH nuo t uždarymo iki t+h. Tik long. Mokestis 0,05 % (perp) ir 0,1 % (spot).
Periodai: 2019–2021 ir 2022-01 – 2026-11. Paleisti: freqtrade/.venv/bin/python papers/54_coinbase_premium/test.py"""
import json, os
import numpy as np, pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(D)
def st(e, a, b):
    e = e[(e.index >= a) & (e.index < b)]; e = e / e.iloc[0]
    y = (e.index[-1] - e.index[0]).days / 365.25
    return f"{((e.iloc[-1]) ** (1 / y) - 1) * 100:+6.1f}%/m. kr {(e / e.cummax() - 1).min() * 100:4.0f}%"
for coin in ("BTC", "ETH"):
    cb = pd.DataFrame(json.load(open(f"{D}/data/{coin}-USD.json")), columns=["t", "l", "h", "o", "c", "v"])
    cb = pd.Series(cb.c.values, pd.to_datetime(cb.t, unit="s"))
    bn = pd.read_pickle(f"{R}/10_sezoniskumas/data/{coin}USDT.pkl"); bn = pd.Series(bn.c.values, pd.to_datetime(bn.t))
    df = pd.concat([cb.rename("cb"), bn.rename("bn")], axis=1).dropna()
    df = df[df.index >= "2019-01-01"]
    prem = df.cb / df.bn - 1
    adj = prem - prem.rolling(24 * 7, min_periods=24 * 3).median()
    r = df.bn.pct_change().shift(-1).fillna(0)        # grąža nuo t iki t+1
    print(f"\n== {coin} == valandų {len(df)}, premija mediana {prem.median()*100:.3f} %, adj std {adj.std()*100:.3f} %")
    print(f"laikyti: 2019–21 {st((1+r).cumprod(), '2019-01-01', '2022-01-01')} | 2022–26 {st((1+r).cumprod(), '2022-01-01', '2027-01-01')}")
    # koreliacija: adj ir būsimos grąžos
    for h in (1, 4, 24):
        fwd = df.bn.pct_change(h).shift(-h)
        print(f"  corr(adj, ateities {h}h grąža): 2019–21 {adj[:'2021'].corr(fwd[:'2021']):+.3f} | 2022–26 {adj['2022':].corr(fwd['2022':]):+.3f}")
    for sign, nm in ((1, "premija > k (long)"), (-1, "nuolaida < −k (kontrarinis long)")):
        for k in (0.0, 0.0005, 0.001, 0.002):
            for h in (1, 4, 24):
                sig = (sign * adj > k).astype(float)
                pos = sig.rolling(h, min_periods=1).max()      # laikyti h valandų po signalo
                for fee in (0.0005, 0.001):
                    eq = (1 + r * pos - pos.diff().abs().fillna(0) * fee).cumprod()
                    if fee == 0.0005: s1 = (st(eq, '2019-01-01', '2022-01-01'), st(eq, '2022-01-01', '2027-01-01'))
                    else: s2 = st(eq, '2022-01-01', '2027-01-01')
                print(f"{nm:34s} k={k*100:.2f}% h={h:2d}: rinkoje {pos.mean()*100:3.0f}% | 0,05%: 2019–21 {s1[0]} | 2022–26 {s1[1]} | 0,1%: 2022–26 {s2}")
    # dienos versija: vidutinė dienos adj premija > 0 -> laikyti kitą dieną
    da = adj.resample("1D").mean(); dr = df.bn.resample("1D").last().pct_change().shift(-1).fillna(0)
    for sign in (1, -1):
        pos = (sign * da > 0).astype(float)
        eq = (1 + dr * pos - pos.diff().abs().fillna(0) * 0.001).cumprod()
        print(f"dienos {'premija' if sign>0 else 'nuolaida'} > 0: 2019–21 {st(eq, '2019-01-01', '2022-01-01')} | 2022–26 {st(eq, '2022-01-01', '2027-01-01')}")
