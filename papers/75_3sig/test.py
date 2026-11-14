"""75: Jason Kelly „The 3% Signal“ (2015) ir 9Sig (TQQQ). Kas ketvirtį: tikslinė akcijų dalies vertė = praeito ketvirčio tikslas × (1 + g)
(3Sig: g = 3 %, IWM/AGG 80/20; 9Sig: g = 9 %, TQQQ/AGG 60/40). Perteklius parduodamas į AGG, trūkumas perkamas iš AGG (kiek leidžia AGG).
„30 down, stick around“: jei akcijų ETF ketvirčio uždarymas > 30 % žemiau 2 m. maksimumo – ignoruojami 4 pardavimo signalai.
Kai AGG > 60 % portfelio (3Sig) – perbalansuojama į pradinį santykį (knygos taisyklė, metinė). Kaštai 0,03 %.
Sintetinis TQQQ 2000–2010: 3 × QQQ dienos grąža − 0,95 %/m. − 2 × BIL. Paleisti: quantconnect-lean/.venv/bin/python papers/75_3sig/test.py"""
import os, numpy as np, pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(D); ROOT = os.path.dirname(R)
L = lambda t: pd.read_csv(f"{R}/59_ibs/data/{t}.csv", index_col=0, parse_dates=True).Close
E = pd.read_csv(f"{ROOT}/etf-rotation/data/close.csv", index_col=0, parse_dates=True)
qqq, iwm, spy = L("QQQ"), L("IWM"), L("SPY"); bil = L("BIL").pct_change().reindex(qqq.index).fillna(0.0001)
agg = E.AGG.reindex(qqq.index).ffill(); ief = L("IEF").reindex(qqq.index).ffill()
bond = agg.pct_change().fillna(ief.pct_change()).fillna(0)                  # AGG nuo 2003, prieš tai IEF
syn = (3 * qqq.pct_change() - 0.0095 / 252 - 2 * bil).fillna(0)
tq = E.TQQQ.reindex(qqq.index).pct_change(); tqr = tq.where(tq.notna(), syn).fillna(0)
def sig(stock_r, g, w0, reset_bonds=None):
    idx = stock_r.index; S = w0; B = 1 - w0; target = S; eq = []; ignore = 0
    px = (1 + stock_r).cumprod(); qend = idx.to_series().groupby(idx.to_period("Q")).last().values
    for t in idx:
        S *= 1 + stock_r[t]; B *= 1 + bond[t]
        if t in qend:
            target *= 1 + g; hi2 = px[:t].iloc[-504:].max()
            if px[t] < 0.7 * hi2 and ignore == 0: ignore = 4
            diff = S - target
            if diff > 0:
                if ignore > 0: ignore -= 1; target = S
                else: S -= diff; B += diff * (1 - 0.0003)
            else:
                buy = min(-diff, B); B -= buy; S += buy * (1 - 0.0003)
                target = S if buy < -diff else target
            if reset_bonds and B / (S + B) > reset_bonds and t.month == 12:
                tot = S + B; S, B = tot * w0, tot * (1 - w0); target = S
        eq.append(S + B)
    return pd.Series(eq, idx)
def st(e, a, b):
    e = e[a:b]; e = e / e.iloc[0]; y = (e.index[-1] - e.index[0]).days / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+5.1f}% kr {(e / e.cummax() - 1).min() * 100:3.0f}%"
PER = [("2000", "2009"), ("2010", "2016"), ("2017", "2026")]
print("periodai: 2000–09 | 2010–16 (po knygos: 2015+) | 2017–26")
print("SPY laikyti        " + " | ".join(st(spy, a, b) for a, b in PER))
print("QQQ laikyti        " + " | ".join(st(qqq, a, b) for a, b in PER))
print("TQQQ (sint.) laik. " + " | ".join(st((1 + tqr).cumprod(), a, b) for a, b in PER))
print("3Sig IWM/AGG 80/20 " + " | ".join(st(sig(iwm.pct_change().fillna(0), 0.03, 0.8, 0.6), a, b) for a, b in PER))
print("3Sig QQQ/AGG 80/20 " + " | ".join(st(sig(qqq.pct_change().fillna(0), 0.03, 0.8, 0.6), a, b) for a, b in PER))
print("9Sig TQQQ/AGG 60/40" + " | ".join(st(sig(tqr, 0.09, 0.6), a, b) for a, b in PER))
print("9Sig + reset >60 % " + " | ".join(st(sig(tqr, 0.09, 0.6, 0.6), a, b) for a, b in PER))
fix = (0.6 * tqr + 0.4 * bond)   # palyginimui: kasdien perbalansuojamas 60/40 TQQQ/AGG
print("60/40 TQQQ/AGG kasd." + " | ".join(st((1 + fix).cumprod(), a, b) for a, b in PER))
