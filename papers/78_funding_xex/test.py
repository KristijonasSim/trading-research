"""78: Funding skirtumo arbitražas Binance ↔ Bybit (populiarus „funding arbitrage“): long perp biržoje su mažesniu funding, short – su didesniu.
Kainos kojos atsveria viena kitą (bazės skirtumas tarp biržų ignoruojamas – optimistiška). Signalas – praeitų 3 periodų (8 h) vidutinis skirtumas.
Atidaroma kai |skirtumas| > slenkstis, uždaroma kai ženklas apsiverčia. Kaštai: 4 kojos × 0,05 % (taker) arba 0,02 % (maker) už atidarymą ir uždarymą.
Kapitalas = vienos kojos nominalas (kiekviena koja 2x svertu). Funding sumuojamas į 8 h intervalus. Paleisti: freqtrade/.venv/bin/python papers/78_funding_xex/test.py"""
import json, os
import numpy as np, pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(D))
FB = f"{ROOT}/freqtrade/user_data/data/binance/futures"
def st(x):
    e = (1 + x).cumprod(); y = (x.index[-1] - x.index[0]).days / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+5.1f}%/m. kr {(e / e.cummax() - 1).min() * 100:4.1f}%"
res = {}
print("Binance 2021-08 – 2026-11. moneta: vid. |skirtumas| bp/8h | slenkstis 1 bp ir 3 bp, taker / maker")
for c in "BTC ETH XRP BNB SOL DOGE ADA TRX LINK AVAX LTC DOT".split():
    b = pd.read_feather(f"{FB}/{c}_USDT_USDT-1h-funding_rate.feather"); b = pd.Series(b.funding_rate.values, pd.to_datetime(b.date)).resample("8h").sum()
    y = json.load(open(f"{D}/data/{c}.json")); y = pd.Series({pd.to_datetime(int(k), unit="ms", utc=True): v for k, v in y.items()}).sort_index().resample("8h").sum()
    df = pd.concat([b.rename("b"), y.rename("y")], axis=1, sort=True).dropna(); df = df[(df.b != 0) | (df.y != 0)]
    diff = df.y - df.b                    # >0: short Bybit, long Binance gauna diff
    sigv = diff.rolling(3).mean().shift(1)
    for fee, lab in ((0.0005, "taker"), (0.0002, "maker")):
        for thr in (0.0001, 0.0003):
            pos = pd.Series(0.0, df.index); cur = 0
            for i, t in enumerate(df.index):
                s = sigv.iloc[i]
                if np.isnan(s): continue
                if cur == 0 and abs(s) > thr: cur = np.sign(s)
                elif cur != 0 and np.sign(s) != cur: cur = 0
                pos.iloc[i] = cur
            pnl = pos * diff - pos.diff().abs().fillna(0) * 4 * fee
            res[(c, lab, thr)] = pnl
    p = res[(c, "taker", 0.0001)]; pm = res[(c, "maker", 0.0001)]
    print(f"{c:5s} {diff.abs().mean()*1e4:5.2f} bp | slenkstis 1 bp: taker {st(p)} / maker {st(pm)} | 3 bp: taker {st(res[(c, 'taker', 0.0003)])} / maker {st(res[(c, 'maker', 0.0003)])}")
for lab in ("taker", "maker"):
    for thr in (0.0001, 0.0003):
        port = pd.concat([v for k, v in res.items() if k[1] == lab and k[2] == thr], axis=1, sort=True).fillna(0).mean(axis=1)
        print(f"12 monetų krepšelis {lab} slenkstis {thr*1e4:.0f} bp: visas {st(port)} | 2022–26 {st(port['2022':])} | 2024–26 {st(port['2024':])}")
