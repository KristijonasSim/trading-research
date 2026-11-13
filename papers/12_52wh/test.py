#!/usr/bin/env python3
"""#12 52 savaičių maksimumo momentum (George, Hwang 2004, J. Finance).
Kas mėnesį S&P 500 akcijos (tik tuo metu indekse) reitinguojamos pagal kaina / 52 sav. maksimumas.
Long: arčiausiai maksimumo top 10 % (ar 50 akc.); short: toliausiai nuo jo 10 %. Laikymas 1 arba 6 mėn.
(6 mėn. – 6 persidengiančios kohortos, kaip straipsnyje). Mokestis 0,1 %. Duomenys kaip #7 (../07_lowvol)."""
import os, numpy as np, pandas as pd
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../07_lowvol"))
exec(open("test.py").read().split("W = {k")[0])
os.chdir("../12_52wh")
hi = C.rolling(252, min_periods=240).max()
ratio = C / hi
mom = C.shift(21) / C.shift(252) - 1
mi = {d: i for i, d in enumerate(me)}


def target(dt, kind, side, q):
    m = [t for t in members(dt) if t in C.columns and not np.isnan(C.at[dt, t])]
    s = (ratio if kind == "52wh" else mom).loc[dt, m].dropna().sort_values(ascending=False)
    k = max(int(len(s) * q), 1) if q < 1 else int(q)
    if side == "long": return pd.Series(1 / k, s.index[:k])
    if side == "short": return pd.Series(1 / k, s.index[-k:])
    return pd.concat([pd.Series(0.5 / k, s.index[:k]), pd.Series(-0.5 / k, s.index[-k:])])


def bt(kind="52wh", side="long", q=0.1, hold=1):
    T = {dt: target(dt, kind, side, q) for dt in me[:-1]}
    W = pd.DataFrame(0.0, me[:-1], C.columns)
    for j, dt in enumerate(me[:-1]):
        acc = pd.Series(dtype=float)
        for h in range(hold):
            if j - h >= 0: acc = acc.add(T[me[j - h]] / hold, fill_value=0)
        W.loc[dt, acc.index] = acc.values
    turn = W.diff().abs().sum(axis=1).reindex(C.index).fillna(0).shift(1).fillna(0)
    held = W.reindex(C.index).ffill().fillna(0).shift(1).fillna(0)
    return ((held * R.fillna(0)).sum(axis=1) - turn * FEE)[days]


def st(r, a, b):
    r = r[a:b]; eq = (1 + r).cumprod(); y = len(r) / 252
    return [f"{(eq.iloc[-1] ** (1 / y) - 1) * 100:+.1f}", f"{(eq / eq.cummax() - 1).min() * 100:.0f}", f"{r.mean() / r.std() * np.sqrt(252):.2f}"]


S = {
    "52wh long top 10 %, 1 mėn.": bt("52wh", "long", 0.1, 1),
    "52wh long top 10 %, 6 mėn.": bt("52wh", "long", 0.1, 6),
    "52wh long top 50 akc., 6 mėn.": bt("52wh", "long", 50, 6),
    "52wh long-short 10 %, 6 mėn.": bt("52wh", "ls", 0.1, 6),
    "52wh long-short 30 %, 6 mėn.": bt("52wh", "ls", 0.3, 6),
    "12-1 momentum long top 10 %, 6 mėn.": bt("mom", "long", 0.1, 6),
}
ew = pd.DataFrame(0.0, me[:-1], C.columns)
for dt in me[:-1]:
    m = [t for t in members(dt) if t in C.columns and not np.isnan(C.at[dt, t])]; ew.loc[dt, m] = 1 / len(m)
S["Visos (lygiavertis)"] = (ew.reindex(C.index).ffill().fillna(0).shift(1).fillna(0) * R.fillna(0)).sum(axis=1)[days]
S["SPY"] = rs[days].fillna(0)
per = [("2002", "2013"), ("2014", "2026"), ("2020", "2026")]
out = "| Variantas | " + " | ".join(f"{a}–{b} %/m | kritimas | Sharpe" for a, b in per) + " |\n|" + "---|" * 10 + "\n"
for k, r in S.items():
    out += f"| {k} | " + " | ".join(" | ".join(st(r, a, b)) for a, b in per) + " |\n"
yr = pd.DataFrame({k: (1 + r["2014":]).groupby(r["2014":].index.year).prod() - 1 for k, r in S.items()}).mul(100).round(1)
out += "\nMetai (%):\n\n" + yr.T.to_markdown()
print(out); open("REZULTATAI.txt", "w").write(out + "\n")
