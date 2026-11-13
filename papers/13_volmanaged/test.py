#!/usr/bin/env python3
"""#13 Volatilumu valdomi portfeliai (Moreira, Muir 2017, J. Finance).
Kas mėnesį SPY dalis = c / praeito mėnesio realizuota dispersija (c parinkta taip, kad vidutinė dalis ~1
naudojant TIK praeitį – plečiamas langas), apribota 1x arba 2x. Likutis – 3 mėn. T-bill (^IRX), skolinamasi ta pačia +1 %.
Variantai: dispersija (straipsnis), volatilumas (1/σ), tikslinis 15 % vol. Mokestis 0,05 % nuo apyvartos.
Periodai: 1994–2015 (straipsnio duomenys iki 2015), 2016–2026."""
import os, numpy as np, pandas as pd, yfinance as yf
if not os.path.exists("data/px.pkl"):
    yf.download(["SPY", "^IRX", "QQQ"], start="1993-01-01", end="2026-11-13", auto_adjust=True, progress=False)["Close"].to_pickle("data/px.pkl")
P = pd.read_pickle("data/px.pkl")
FEE = 0.0005


def run(asset="SPY", mode="var", cap=1.0, tv=0.15, daily=False):
    p = P[asset].dropna(); idx = p.index; r = p.pct_change().fillna(0)
    rf = (P["^IRX"].reindex(idx).ffill() / 100 / 252).fillna(0)
    me = pd.Series(idx, idx).groupby(idx.to_period("M")).last().values
    rv = r.rolling(21).var() * 252
    if mode == "var": raw = 1 / rv
    elif mode == "vol": raw = 1 / np.sqrt(rv)
    else: raw = tv / np.sqrt(rv)
    if mode in ("var", "vol"):   # normalizacija tik iš praeities: vidutinė dalis = 1
        raw = raw / raw.expanding(252).mean()
    w = raw.clip(upper=cap)
    if not daily:
        w = w.loc[me].reindex(idx).ffill()
    w = w.shift(1).fillna(0)
    fin = np.where(w > 1, rf + 0.01 / 252, rf)
    turn = w.diff().abs().fillna(0)
    return w * r + (1 - w) * fin - turn * FEE, w


def st(r, a, b):
    r = r[a:b]; eq = (1 + r).cumprod(); y = len(r) / 252
    return [f"{(eq.iloc[-1] ** (1 / y) - 1) * 100:+.1f}", f"{(eq / eq.cummax() - 1).min() * 100:.0f}", f"{r.mean() / r.std() * np.sqrt(252):.2f}"]


S = {}
for a in ["SPY", "QQQ"]:
    S[f"{a} laikyti"] = (P[a].dropna().pct_change().fillna(0), None)
    for mode, cap in [("var", 1), ("var", 2), ("vol", 1), ("vol", 2), ("target", 1), ("target", 2)]:
        S[f"{a} {mode} ≤{cap}x"] = run(a, mode, cap)
    S[f"{a} target ≤2x, kasdien"] = run(a, "target", 2, daily=True)
per = [("1994", "2015"), ("2016", "2026"), ("2020", "2026")]
out = "| Variantas | vid. dalis | " + " | ".join(f"{a}–{b} %/m | kritimas | Sharpe" for a, b in per) + " |\n|" + "---|" * 11 + "\n"
for k, (r, w) in S.items():
    out += f"| {k} | {'' if w is None else round(w['2000':].mean(), 2)} | " + " | ".join(" | ".join(st(r, a, b)) for a, b in per) + " |\n"
yr = pd.DataFrame({k: (1 + r["2016":]).groupby(r["2016":].index.year).prod() - 1 for k, (r, w) in S.items()}).mul(100).round(1)
out += "\nMetai (%):\n\n" + yr.T.to_markdown()
print(out); open("REZULTATAI.txt", "w").write(out + "\n")
