#!/usr/bin/env python3
"""#14 Akcijų sezoniškumas (Heston, Sadka 2008, JFE): akcijos, kurios tą patį kalendorinį mėnesį praeitais
metais uždirbdavo daugiausia, ir šįmet tą mėnesį uždirba daugiau.
Kas mėnesį S&P 500 (tik tuo metu indekse, duomenys kaip #7): signalas = vidutinė grąža tą patį mėnesį
per paskutinius 2–10 metų (min. 3 m.). Long top 10 % / 50 akc., long-short 10 %. Mokestis 0,1 %."""
import os, numpy as np, pandas as pd
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../07_lowvol"))
exec(open("test.py").read().split("W = {k")[0])
os.chdir("../14_seasonality")
mc = C.resample("ME").last()
mr = mc.pct_change(fill_method=None)            # mėnesio grąža (indeksas – mėnesio pabaiga)
# signalas mėnesiui M: vidurkis tų pačių mėnesių per ankstesnius 1..10 metų (lag 12, 24, ... 120)
lags = [mr.shift(12 * k) for k in range(1, 11)]
cnt = sum(l.notna().astype(int) for l in lags)
sig = sum(l.fillna(0) for l in lags) / cnt.replace(0, np.nan)
sig = sig.where(cnt >= 3)
mpos = {p: d for p, d in zip(mc.index.to_period("M"), mc.index)}


def target(dt, side, q):
    m = [t for t in members(dt) if t in C.columns and not np.isnan(C.at[dt, t])]
    nxt = (pd.Period(dt, "M") + 1)
    if nxt not in mpos: return pd.Series(dtype=float)
    s = sig.loc[mpos[nxt], [x for x in m if x in sig.columns]].dropna().sort_values(ascending=False)
    if len(s) < 50: return pd.Series(dtype=float)
    k = max(int(len(s) * q), 1) if q < 1 else int(q)
    if side == "long": return pd.Series(1 / k, s.index[:k])
    if side == "short": return pd.Series(1 / k, s.index[-k:])
    return pd.concat([pd.Series(0.5 / k, s.index[:k]), pd.Series(-0.5 / k, s.index[-k:])])


def bt(side="long", q=0.1):
    W = pd.DataFrame(0.0, me[:-1], C.columns)
    for dt in me[:-1]:
        w = target(dt, side, q)
        if len(w): W.loc[dt, w.index] = w.values
    turn = W.diff().abs().sum(axis=1).reindex(C.index).fillna(0).shift(1).fillna(0)
    held = W.reindex(C.index).ffill().fillna(0).shift(1).fillna(0)
    return ((held * R.fillna(0)).sum(axis=1) - turn * FEE)[days]


def st(r, a, b):
    r = r[a:b]; eq = (1 + r).cumprod(); y = len(r) / 252
    return [f"{(eq.iloc[-1] ** (1 / y) - 1) * 100:+.1f}", f"{(eq / eq.cummax() - 1).min() * 100:.0f}", f"{r.mean() / r.std() * np.sqrt(252):.2f}"]


S = {"Long top 10 %": bt("long", 0.1), "Long top 50 akc.": bt("long", 50), "Long-short 10 %": bt("ls", 0.1), "Long blogiausi 10 %": bt("short", 0.1)}
ew = pd.DataFrame(0.0, me[:-1], C.columns)
for dt in me[:-1]:
    m = [t for t in members(dt) if t in C.columns and not np.isnan(C.at[dt, t])]; ew.loc[dt, m] = 1 / len(m)
S["Visos (lygiavertis)"] = (ew.reindex(C.index).ffill().fillna(0).shift(1).fillna(0) * R.fillna(0)).sum(axis=1)[days]
S["SPY"] = rs[days].fillna(0)
per = [("2004", "2013"), ("2014", "2026"), ("2020", "2026")]
out = "| Variantas | " + " | ".join(f"{a}–{b} %/m | kritimas | Sharpe" for a, b in per) + " |\n|" + "---|" * 10 + "\n"
for k, r in S.items():
    out += f"| {k} | " + " | ".join(" | ".join(st(r, a, b)) for a, b in per) + " |\n"
yr = pd.DataFrame({k: (1 + r["2014":]).groupby(r["2014":].index.year).prod() - 1 for k, r in S.items()}).mul(100).round(1)
out += "\nMetai (%):\n\n" + yr.T.to_markdown()
print(out); open("REZULTATAI.txt", "w").write(out + "\n")
