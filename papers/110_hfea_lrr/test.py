#!/usr/bin/env python3
"""#110 Garsios rizikingos sverto ETF strategijos.
A) Hedgefundie's Excellent Adventure (Bogleheads 2019): 55 % UPRO + 45 % TMF, perbalansuoti kas ketvirtį.
   Variantai: 60/40 TQQQ/TMF; HFEA tik kai SPY > SMA200 (kitaip T-bills).
B) Gayed & Bilello „Leverage for the Long Run“ (2016, Dow Award): 3x indeksas, kai indeksas > SMA200, kitaip T-bills.
   Signalas uždarymu, sandoris kitos dienos uždarymu. Ant SPY→UPRO, QQQ→TQQQ, SOXX→SOXL.
3x sintetiniai: 3 × bazinė − 2 × trumpųjų palūkanų − 0,95 %/m. (TMF iš VUSTX/TLT, ilgųjų obligacijų fondas). Kaštai 0,1 % nuo apyvartos.
Periodai: 2000–09 (dot-com + 2008), 2010–19, 2020–26."""
import os, numpy as np, pandas as pd
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
L = lambda t: pd.read_csv(f"{D}/{t}.csv", index_col=0, parse_dates=True).Close
spy, qqq, soxx = L("SPY"), L("QQQ"), L("SOXX")
vr = L("VUSTX").pct_change(); tr = L("TLT").pct_change(); bond = pd.concat([vr[vr.index <= tr.index[0]], tr.iloc[1:]])
idx = spy.index[spy.index >= "1999-06-01"]
rf = (L("IRX") / 100 / 252).reindex(idx).ffill().fillna(0)
r = lambda s: s.pct_change().reindex(idx)
x3 = lambda rr: 3 * rr - 2 * rf - 0.0095 / 252
U, T, S, B = x3(r(spy)), x3(r(qqq)), x3(r(soxx)), x3(bond.reindex(idx))
def stat(x, a, b):
    x = x[a:b].dropna(); e = (1 + x).cumprod(); y = len(x) / 252
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+6.1f}% DD {(e / e.cummax() - 1).min() * 100:4.0f}%"
def yrs(x):
    y = (1 + x["2018":]).groupby(x["2018":].index.year).prod() - 1
    return " ".join(f"{k % 100:02d}:{v * 100:+.0f}" for k, v in y.items())
def rebal(assets, w, freq="Q", gate=None):
    A = pd.concat(assets, axis=1).fillna(0); A.columns = range(len(assets)); W = np.array(w, float)
    q = A.index.to_period(freq); out = []; h = W.copy()
    on_prev = True
    for i, d in enumerate(A.index):
        on = True if gate is None else bool(gate.iloc[i - 1]) if i > 0 else False
        if not on: out.append(rf.iloc[i] - (0.001 if on_prev else 0)); on_prev = False; h = W.copy(); continue
        cost = 0.001 if not on_prev else 0
        rr = (h * A.iloc[i].values).sum(); h = h * (1 + A.iloc[i].values); h = h / h.sum()
        if i + 1 < len(A) and q[i + 1] != q[i]: cost += np.abs(h - W).sum() * 0.001; h = W.copy()
        out.append(rr - cost); on_prev = True
    return pd.Series(out, A.index)
def lrr(base, lev, band=0.0):
    s = base.reindex(idx); m = s.rolling(200).mean()
    sig = pd.Series(np.nan, idx); sig[s > m * (1 + band)] = 1; sig[s < m * (1 - band)] = 0; sig = sig.ffill().fillna(0)
    pos = sig.shift(1).fillna(0)  # signalas uždarymu, įėjimas kitą d. uždarymu -> grąža nuo i+2
    pos = pos.shift(1).fillna(0)
    return pos * lev + (1 - pos) * rf - pos.diff().abs().fillna(0) * 0.001
P = [("2000", "2009"), ("2010", "2019"), ("2020", "2026")]
rows = {"Laikyti SPY": r(spy), "Laikyti QQQ": r(qqq), "Laikyti UPRO": U, "Laikyti TQQQ": T, "Laikyti SOXL": S,
        "HFEA 55/45 UPRO/TMF": rebal([U, B], [.55, .45]), "HFEA 60/40 TQQQ/TMF": rebal([T, B], [.6, .4]),
        "HFEA kai SPY>SMA200": rebal([U, B], [.55, .45], gate=(spy > spy.rolling(200).mean()).reindex(idx)),
        "LRR SPY→UPRO": lrr(spy, U), "LRR QQQ→TQQQ": lrr(qqq, T), "LRR SOXX→SOXL": lrr(soxx, S),
        "LRR QQQ→TQQQ, 3 % juosta": lrr(qqq, T, 0.03), "LRR SOXX→SOXL, 3 % juosta": lrr(soxx, S, 0.03)}
print(f"{'':28s} {'2000–09':18s} | {'2010–19':18s} | {'2020–26':18s} | 2018+")
for k, v in rows.items():
    print(f"{k:28s} " + " | ".join(stat(v, a, b) for a, b in P) + " | " + yrs(v), flush=True)
