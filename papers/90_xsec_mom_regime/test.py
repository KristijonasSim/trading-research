"""90: Kripto skerspjūvio momentum su rinkos būsenos filtru (momentum ir rinkos būsenos – Cooper, Gutierrez, Hameed 2004; kripto – Grobys ir kt.):
long top 20 % iš top 50 (pagal 30 d. apyvartą, amžius ≥ 60 d., su išregistruotomis) pagal 1–4 sav. grąžą, tik kai BTC > 200 d. SMA (arba > 100 d.), kitaip grynieji.
Perbalansavimas kas savaitę, 0,1 % mokestis. Paleisti: python3 papers/90_xsec_mom_regime/test.py"""
import os, sys
import pandas as pd, numpy as np
D = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(D); sys.path.insert(0, R)
import xsec
P, V = xsec.load(); Rr = P.pct_change(fill_method=None); age = P.notna().cumsum(); liq = V.rolling(30, min_periods=20).mean()
btc = P["BTCUSDT"]
def run(L, sma, k=0.2, topn=50):
    reg = btc > btc.rolling(sma).mean(); S = P.pct_change(L, fill_method=None)
    eq, dates, wprev = [1.0], [P.index[0]], pd.Series(0.0, P.columns)
    for i in range(210, len(P) - 1, 7):
        j = min(i + 7, len(P) - 1); w = pd.Series(0.0, P.columns)
        if reg.iloc[i]:
            ok = (age.iloc[i] >= 60) & P.iloc[i].notna() & S.iloc[i].notna() & liq.iloc[i].notna()
            uni = liq.iloc[i][ok].nlargest(topn).index; sc = S.iloc[i][uni].sort_values(); n = max(1, int(len(sc) * k)); w[sc.index[-n:]] = 1 / n
        cost = (w - wprev).abs().sum() * 0.001; rr = Rr.iloc[i + 1:j + 1][w[w > 0].index].fillna(0)
        val = ((1 + rr).cumprod() * w[w > 0]).sum(axis=1) + (1 - w.sum()) if w.sum() > 0 else pd.Series(1.0, Rr.index[i + 1:j + 1])
        e0 = eq[-1] * (1 - cost); eq += list(e0 * val.values); dates += list(Rr.index[i + 1:j + 1]); wprev = w
    return pd.Series(eq, dates)
print("periodai 2018–21 | 2022–26 (CAGR, kritimas, metai)")
for nm, e in [("BTC laikyti", btc / btc.iloc[0])] + [(f"momentum {L//7} sav., BTC > SMA{s}", run(L, s)) for L in (7, 14, 28) for s in (100, 200)]:
    a, b = xsec.stats(e, "2018-01-01", "2022-01-01"), xsec.stats(e, "2022-01-01", "2027-01-01")
    print(f"{nm:32s} {a['cagr']:+7.1f}% kr {a['dd']:5.1f}% | {b['cagr']:+7.1f}% kr {b['dd']:5.1f}% | {b['yearly']}", flush=True)
# palyginimui: BTC su tuo pačiu filtru
for s in (100, 200):
    pos = (btc > btc.rolling(s).mean()).astype(float).shift(1).fillna(0); e = (1 + btc.pct_change().fillna(0) * pos - pos.diff().abs().fillna(0) * 0.001).cumprod()
    a, b = xsec.stats(e, "2018-01-01", "2022-01-01"), xsec.stats(e, "2022-01-01", "2027-01-01")
    print(f"{'BTC kai > SMA' + str(s):32s} {a['cagr']:+7.1f}% kr {a['dd']:5.1f}% | {b['cagr']:+7.1f}% kr {b['dd']:5.1f}% | {b['yearly']}")
