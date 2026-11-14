"""58: Taker buy ratio (agresyvių pirkėjų dalis apyvartoje) – A) laiko eilutė BTC/ETH (CryptoQuant „Taker Buy Sell Ratio“),
B) skerspjūvis top 50 monetų (order imbalance straipsniai, pvz. Chordia, Subrahmanyam 2004 metodas kripto).
Dienos duomenys, 1 d. vėlavimas (A), B – papers/xsec.py variklis (perbalansavimas uždarymu, grąža nuo kitos dienos), mokestis 0,1 %.
Paleisti: python3 papers/58_taker_imbalance/test.py"""
import glob, os, sys, json
import pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(D); sys.path.insert(0, R)
import xsec
tb = {}
for f in glob.glob(f"{D}/data/*.csv"):
    d = pd.read_csv(f)
    if len(d) < 90: continue
    tb[os.path.basename(f)[:-4]] = pd.Series((d.tbqv / d.qv.replace(0, float("nan"))).values, pd.to_datetime(d.t, unit="ms"))
TB = pd.DataFrame(tb).sort_index()
P, V = xsec.load(); TB = TB.reindex(index=P.index, columns=P.columns)
def st(e, a, b):
    e = e[(e.index >= a) & (e.index < b)]; e = e / e.iloc[0]; y = (e.index[-1] - e.index[0]).days / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+6.1f}%/m. kr {(e / e.cummax() - 1).min() * 100:4.0f}%"
PER = [("2018-01-01", "2022-01-01"), ("2022-01-01", "2027-01-01")]
print("periodai: 2018–21 | 2022–26")
for c in ("BTCUSDT", "ETHUSDT"):
    px = P[c].dropna(); tbr = TB[c].reindex(px.index); r = px.pct_change().shift(-1).fillna(0)
    def show(nm, pos):
        pos = pos.fillna(0); e = (1 + r * pos - pos.diff().abs().fillna(0) * 0.001).cumprod()
        print(f"{c[:3]} {nm:36s} " + " | ".join(st(e, a, b) for a, b in PER) + f" | rinkoje {pos.mean()*100:3.0f}%")
    print(); show("laikyti", pd.Series(1.0, px.index))
    for n in (1, 3, 7, 14):
        m = tbr.rolling(n).mean()
        show(f"A TBR {n} d. vid. > 0,5", (m > 0.5).astype(float))
        show(f"A TBR {n} d. vid. > 90 d. mediana", (m > tbr.rolling(90).median()).astype(float))
        show(f"A TBR {n} d. vid. < 90 d. mediana (kontr.)", (m < tbr.rolling(90).median()).astype(float))
print("\nB skerspjūvis (top 50 pagal apyvartą, long 20 % / long-short):")
out = {}
for n in (1, 7, 28):
    S = TB.rolling(n, min_periods=max(1, n // 2)).mean()
    for step in ((1, 7) if n == 1 else (7,)):
        for sign, lab in ((1, "aukščiausias TBR"), (-1, "žemiausias TBR")):
            for side in ("long", "ls"):
                e = xsec.run(P, V, lambda p, S=S, sign=sign: sign * S, step, side=side)
                s1, s2 = xsec.stats(e, "2018-01-01", "2022-01-01"), xsec.stats(e, "2022-01-01", "2027-01-01")
                k = f"TBR {n} d., kas {step} d., {lab}, {side}"; out[k] = (s1, s2)
                print(f"{k:45s} 2018–21 {s1['cagr']:+7.1f}% kr {s1['dd']}% | 2022–26 {s2['cagr']:+7.1f}% kr {s2['dd']}% | {s2['yearly']}", flush=True)
e = xsec.run(P, V, lambda p: p.pct_change(7, fill_method=None), 7, side="bench")
print("Top50 lygiais svoriais:", xsec.stats(e, "2018-01-01", "2022-01-01")["cagr"], xsec.stats(e, "2022-01-01", "2027-01-01"))
