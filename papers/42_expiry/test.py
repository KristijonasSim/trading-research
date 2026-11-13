#!/usr/bin/env python3
"""#42 BTC/ETH opcionų galiojimo pabaigos efektas (Deribit mėnesinis galiojimas – paskutinis mėnesio penktadienis 08:00 UTC; „max pain“ teiginiai,
pvz., Kaiko / Glassnode tyrimai). Vidutinė grąža dienomis −5…+5 aplink galiojimą ir paprastos strategijos:
A) laikyti tik savaitę iki galiojimo; B) laikyti tik savaitę po galiojimo. Dienos duomenys 2019–2026 (Deribit mėnesiniai nuo ~2019), 0,1 %."""
import os, numpy as np, pandas as pd
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/binance_1d")
def load(s):
    d = pd.read_csv(f"{D}/{s}USDT.csv"); return pd.Series(d.c.values, pd.to_datetime(d.t, unit="ms"))
for s in ["BTC", "ETH"]:
    p = load(s)["2019-01-01":]; r = p.pct_change()
    fr = p.index[p.index.dayofweek == 4]; exp = pd.Series(fr, fr).groupby(fr.to_period("M")).max().values
    rel = pd.Series(np.nan, p.index)
    pos = {d: i for i, d in enumerate(p.index)}
    tab = {}
    for k in range(-5, 6):
        vals = [r.iloc[pos[e] + k] for e in exp if pos[e] + k < len(r) and pos[e] + k > 0]
        tab[k] = (np.mean(vals) * 100, np.mean(np.array(vals) > 0) * 100)
    print(s, "vid. dienos grąža (%), laimi %: " + " ".join(f"{k:+d}:{v[0]:+.2f}/{v[1]:.0f}" for k, v in tab.items()), "| visų dienų vid.", f"{r.mean()*100:+.2f}")
    for nm, a, b in [("savaitė prieš", -4, 0), ("savaitė po", 1, 5)]:
        w = pd.Series(0.0, p.index)
        for e in exp:
            i = pos[e]
            for k in range(a, b + 1):
                if 0 < i + k < len(w): w.iloc[i + k] = 1
        x = w * r.fillna(0) - w.diff().abs().fillna(0) * 0.001
        for A, B in [("2019", "2022-12-31"), ("2023", "2026-12-31")]:
            xx = x[A:B]; e2 = (1 + xx).cumprod(); y = len(xx) / 365.25
            print(f"  {nm} {A}–{B[:4]}: {(e2.iloc[-1]**(1/y)-1)*100:+.1f}%/m. DD {(e2/e2.cummax()-1).min()*100:.0f}% (laikymas {((1+r[A:B].fillna(0)).prod()**(1/y)-1)*100:+.1f}%)")
