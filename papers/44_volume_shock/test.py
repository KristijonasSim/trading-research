#!/usr/bin/env python3
"""#44 Didelės apyvartos premija (Gervais, Kaniel, Mingelgrin 2001 JF; kripto faktorius – Liu, Tsyvinski, Wu 2022 „Common risk factors in cryptocurrency“).
Kas savaitę iš top 50 (pagal 30 d. apyvartą, su išregistruotomis) pirkti 20 % su didžiausiu apyvartos šuoliu (7 d. / 90 d. vidutinė apyvarta).
Taip pat atvirkščiai (mažiausias šuolis). Mokestis 0,1 %. Variklis papers/xsec.py."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from xsec import load, run, stats
P, V = load()
btc = P["BTCUSDT"] / P["BTCUSDT"].iloc[0]
shock = V.rolling(7, min_periods=5).mean() / V.rolling(90, min_periods=60).mean()
tests = {"Top50 lygiais svoriais": lambda: run(P, V, lambda p: p.pct_change(7, fill_method=None), 7, side="bench"),
         "Apyvartos šuolis, didžiausi 20 %": lambda: run(P, V, lambda p: shock, 7),
         "Apyvartos šuolis, mažiausi 20 %": lambda: run(P, V, lambda p: -shock, 7),
         "Šuolis + teigiama sav. grąža": lambda: run(P, V, lambda p: shock.rank(axis=1, pct=True) + (p.pct_change(7, fill_method=None) > 0) * 1.0, 7),
         "Apyvartos šuolis long-short": lambda: run(P, V, lambda p: shock, 7, side="ls")}
for k, f in tests.items():
    e = f(); print(k, "| 2018–21", stats(e, "2018-01-01", "2021-11-08"), "| 2021–26", stats(e, "2021-11-08", "2027-01-01"), flush=True)
