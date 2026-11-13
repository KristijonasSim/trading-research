"""Kripto skerspjūvio strategijos (straipsniai 1, 2, 5 iš papers/EILE.md) ant visų Binance USDT porų,
įskaitant išregistruotas. Visata: top N pagal 30 d. vidutinę apyvartą (USDT), monetos amžius ≥ 60 d.
Mokestis 0,1 % nuo apyvartos. Kūrimo laikotarpis 2018–2021 (straipsnių duomenys), nematytas 2022-01 – 2026-11.
Paleisti: python3 papers/xsec.py"""
import glob, os, json
import numpy as np, pandas as pd
D = os.path.dirname(os.path.abspath(__file__))
FEE = 0.001
def load():
    px, qv = {}, {}
    for f in glob.glob(f"{D}/data/binance_1d/*.csv"):
        d = pd.read_csv(f)
        if len(d) < 90: continue
        s = os.path.basename(f)[:-4]
        idx = pd.to_datetime(d.t, unit="ms")
        px[s] = pd.Series(d.c.values, idx); qv[s] = pd.Series(d.qv.values, idx)
    P = pd.DataFrame(px).sort_index(); V = pd.DataFrame(qv).sort_index()
    return P[P.index >= "2018-01-01"], V[V.index >= "2018-01-01"]

def run(P, V, signal, step, topn=50, q=0.2, side="long", hold=None):
    """signal: f(P) -> DataFrame score (didesnis = pirkti). step: perbalansavimo dažnis dienomis."""
    R = P.pct_change(fill_method=None)
    age = P.notna().cumsum()
    liq = V.rolling(30, min_periods=20).mean()
    S = signal(P)
    w_prev = pd.Series(0.0, index=P.columns); eq = [1.0]; dates = [P.index[0]]
    for i in range(70, len(P) - 1, step):
        t = P.index[i]
        ok = (age.iloc[i] >= 60) & P.iloc[i].notna() & S.iloc[i].notna() & liq.iloc[i].notna()
        uni = liq.iloc[i][ok].nlargest(topn).index
        if len(uni) < 10: continue
        sc = S.iloc[i][uni].sort_values()
        k = max(1, int(len(sc) * q))
        w = pd.Series(0.0, index=P.columns)
        if side == "bench": w[uni] = 1 / len(uni)
        else:
            w[sc.index[-k:]] = 1 / k
            if side == "ls": w[sc.index[-k:]] = 0.5 / k; w[sc.index[:k]] = -0.5 / k
        cost = (w - w_prev).abs().sum() * FEE
        j = min(i + step, len(P) - 1)
        rr = R.iloc[i + 1:j + 1][w[w != 0].index].fillna(0)   # išregistruota = 0 grąža po paskutinės kainos
        path = (1 + rr).cumprod()
        val = (path * w[w != 0]).sum(axis=1) + (1 - w[w != 0].abs().sum() if side != "ls" else 0)
        if side == "ls": val = 1 + (path - 1).mul(w[w != 0]).sum(axis=1)
        e0 = eq[-1] * (1 - cost)
        eq += list(e0 * val.values); dates += list(rr.index)
        w_prev = w  # supaprastinta: svoriai neperskaičiuojami dėl dreifo
    return pd.Series(eq, dates)

def stats(e, a, b):
    e = e[(e.index >= a) & (e.index < b)]
    if len(e) < 30: return None
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    cagr = (e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1
    dd = (e / e.cummax() - 1).min()
    yr = e.resample("YE").last().pct_change().dropna()
    first = e.resample("YE").last().iloc[0] / e.iloc[0] - 1
    yearly = {str(e.index[0].year): round(first * 100)} | {str(k.year): round(v * 100) for k, v in yr.items()}
    return dict(cagr=round(cagr * 100, 1), dd=round(dd * 100, 1), yearly=yearly)

if __name__ == "__main__":
    P, V = load()
    print("monetų:", P.shape[1], P.index[0].date(), P.index[-1].date(), flush=True)
    btc = P["BTCUSDT"] / P["BTCUSDT"].iloc[0]
    tests = {
        "BTC laikyti": lambda: btc,
        "Top50 lygiais svoriais (kas sav.)": lambda: run(P, V, lambda p: p.pct_change(7, fill_method=None), 7, side="bench"),
    }
    for L in (7, 14, 21, 28):   # 1) momentum (Liu, Tsyvinski, Wu 2022)
        tests[f"1 Momentum {L//7} sav., long top 20 %"] = (lambda L=L: run(P, V, lambda p: p.pct_change(L, fill_method=None), 7))
        tests[f"1 Momentum {L//7} sav., long-short"] = (lambda L=L: run(P, V, lambda p: p.pct_change(L, fill_method=None), 7, side="ls"))
    for L in (1, 3):            # 2) trumpalaikis atšokimas (Dobrynskaya 2023)
        tests[f"2 Atšokimas {L} d., long nuostolingiausi 20 %"] = (lambda L=L: run(P, V, lambda p: -p.pct_change(L, fill_method=None), L))
    tests["2 Atšokimas 1 sav., long nuostolingiausi 20 %"] = lambda: run(P, V, lambda p: -p.pct_change(7, fill_method=None), 7)
    # 5) mažų monetų premija: iš top 200 pagal apyvartą perka mažiausius 20 %
    tests["5 Mažiausios (top 200 apačia), kas sav."] = lambda: run(P, V, lambda p: -V.rolling(30, min_periods=20).mean(), 7, topn=200)
    tests["5 Mažiausios + momentum 3 sav."] = lambda: run(P, V, lambda p: p.pct_change(21, fill_method=None).rank(axis=1, pct=True) - V.rolling(30, min_periods=20).mean().rank(axis=1, pct=True), 7, topn=200)
    out = {}
    for name, f in tests.items():
        e = f()
        out[name] = {"2018-2021": stats(e, "2018-01-01", "2022-01-01"), "2022-2026": stats(e, "2022-01-01", "2027-01-01")}
        print(name, json.dumps(out[name], ensure_ascii=False), flush=True)
    json.dump(out, open(f"{D}/01_kripto_momentum/rezultatai.json", "w"), ensure_ascii=False, indent=1)
    print("XSEC_DONE")
