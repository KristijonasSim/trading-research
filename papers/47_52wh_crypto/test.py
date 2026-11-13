#!/usr/bin/env python3
"""#47 Artumas metų maksimumui kripto skerspjūvyje (George, Hwang 2004 metodas; kripto – Chen ir kt. 2023 „Anchoring in crypto“).
Kas savaitę iš top 50 pirkti 20 % monetų, kurių kaina arčiausiai 365 d. (ir 90 d.) maksimumo. Taip pat long-short. 0,1 %."""
import os, sys, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from xsec import load, run, stats
P, V = load()
def near(L): return lambda p: p / p.rolling(L, min_periods=int(L * 0.6)).max()
tests = {"Top50 lygiais svoriais": lambda: run(P, V, lambda p: p.pct_change(7, fill_method=None), 7, side="bench"),
         "Arčiausiai 365 d. max": lambda: run(P, V, near(365), 7),
         "Arčiausiai 90 d. max": lambda: run(P, V, near(90), 7),
         "Arčiausiai 365 d. max, long-short": lambda: run(P, V, near(365), 7, side="ls")}
for k, f in tests.items():
    e = f(); print(k, "| 2018–21", stats(e, "2018-01-01", "2021-11-08"), "| 2021–26", stats(e, "2021-11-08", "2027-01-01"), flush=True)
