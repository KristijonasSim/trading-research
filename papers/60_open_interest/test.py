"""60: Atvirų pozicijų (OI) signalai – populiarūs teiginiai: A) kaina ir OI kyla kartu = sveikas trendas, kaina kyla OI krentant = shortų uždarymas;
B) OI šuolis (z-balas) = per didelis svertas -> rizika; C) skerspjūvis: monetos su didžiausiu OI augimu (perkaitimas) atsilieka.
Bybit OI (00:00 UTC momentinė reikšmė = ankstesnės dienos uždarymas), Binance spot dienos kainos. Signalas dienos uždarymu, pozicija nuo kitos dienos.
Mokestis 0,1 %. ⚠️ C visata – 30 dabar egzistuojančių monetų (išgyvenusiųjų iškraipymas). Paleisti: quantconnect-lean/.venv/bin/python papers/60_open_interest/test.py"""
import json, os, glob
import numpy as np, pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(D); FEE = 0.001
OI, PX = {}, {}
for f in glob.glob(f"{D}/data/*.json"):
    c = os.path.basename(f)[:-5]; d = json.load(open(f))
    if len(d) < 400: continue
    s = pd.Series({pd.to_datetime(int(k), unit="ms") - pd.Timedelta(days=1): v for k, v in d.items()}).sort_index()
    b = pd.read_csv(f"{R}/data/binance_1d/{c}USDT.csv"); PX[c] = pd.Series(b.c.values, pd.to_datetime(b.t, unit="ms")); OI[c] = s
OI = pd.DataFrame(OI).sort_index(); PX = pd.DataFrame(PX).reindex(OI.index)
OI = OI.where(OI > 0)
def st(e, a, b):
    e = e[(e.index >= a) & (e.index < b)].dropna()
    if len(e) < 60: return "   –"
    e = e / e.iloc[0]; y = (e.index[-1] - e.index[0]).days / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+6.1f}% kr {(e / e.cummax() - 1).min() * 100:4.0f}%"
PER = [("2020-11-01", "2022-01-01"), ("2022-01-01", "2024-01-01"), ("2024-01-01", "2027-01-01")]
print("periodai: 2020-11–21 | 2022–23 | 2024–26")
def ts(c, nm, pos):
    r = PX[c].pct_change().shift(-1).fillna(0); pos = pos.fillna(0)
    e = (1 + r * pos - pos.diff().abs().fillna(0) * FEE).cumprod()
    return " | ".join(st(e, a, b) for a, b in PER) + f" | rinkoje {pos[PX[c].notna()].mean()*100:3.0f}%"
for c in ("BTC", "ETH", "SOL", "XRP"):
    print(f"\n== {c} ==\n laikyti                           {ts(c, '', pd.Series(1.0, OI.index))}")
    p, o = PX[c], OI[c]
    for n in (3, 7, 14):
        dp, do = p.pct_change(n), o.pct_change(n)
        for lab, cond in (("kaina↑ OI↑", (dp > 0) & (do > 0)), ("kaina↑ OI↓", (dp > 0) & (do < 0)), ("kaina↓ OI↓ (išvalymas)", (dp < 0) & (do < 0)), ("kaina↓ OI↑", (dp < 0) & (do > 0))):
            print(f" A {n:2d} d. {lab:24s} {ts(c, '', cond.astype(float))}")
    for w in (30, 90):
        z = (o - o.rolling(w).mean()) / o.rolling(w).std()
        for thr in (1.5, 2.0):
            print(f" B grynieji kai OI z({w}) > {thr}         {ts(c, '', (z <= thr).astype(float))}")
# C skerspjūvis
print("\n== C skerspjūvis (30 monetų, kas savaitę, long 20 %) ==")
R1 = PX.pct_change(fill_method=None)
for n in (7, 28):
    S = OI.pct_change(n, fill_method=None)
    for lab, sgn in (("didžiausias OI augimas", 1), ("mažiausias OI augimas", -1)):
        eq, dates, wprev = [1.0], [OI.index[0]], pd.Series(0.0, OI.columns)
        for i in range(60, len(OI) - 1, 7):
            sc = (sgn * S.iloc[i]).dropna(); sc = sc[PX.iloc[i][sc.index].notna()]
            if len(sc) < 10: continue
            k = max(1, len(sc) // 5); w = pd.Series(0.0, OI.columns); w[sc.nlargest(k).index] = 1 / k
            cost = (w - wprev).abs().sum() * FEE; j = min(i + 7, len(OI) - 1)
            rr = R1.iloc[i + 1:j + 1][w[w > 0].index].fillna(0); val = ((1 + rr).cumprod() * w[w > 0]).sum(axis=1)
            e0 = eq[-1] * (1 - cost); eq += list(e0 * val.values); dates += list(rr.index); wprev = w
        e = pd.Series(eq, dates)
        print(f" OI {n} d. {lab:24s} " + " | ".join(st(e, a, b) for a, b in PER))
    # palyginimui lygiais svoriais
eqw = (1 + R1.fillna(0).mean(axis=1)).cumprod()
print(f" visos lygiais svoriais (kasdien)      " + " | ".join(st(eqw, a, b) for a, b in PER))
