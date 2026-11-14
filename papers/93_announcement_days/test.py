"""93: Makro paskelbimų dienų premija (Savor, Wilson 2013 JFQA „How Much Do Investors Care About Macroeconomic Risk?“): akcijos (ir obligacijos)
uždirba daug daugiau FOMC, NFP (JAV darbo vietų ataskaita), CPI paskelbimo dienomis. Čia: FOMC sprendimo dienos (#11 duomenys) ir NFP (pirmas mėnesio penktadienis –
apytiksliai). Rezultatas: vid. dienos grąža ir strategija „laikyti tik paskelbimo dienomis“ (1x ir 3x), kitu metu BIL. SPY, TLT; Yahoo 1994–2026.
Paskelbta 2013 -> nematytas 2013–2026. Paleisti (iš papers/11_fomc): ../../quantconnect-lean/.venv/bin/python ../93_announcement_days/test.py"""
import os, re, glob, numpy as np, pandas as pd
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../11_fomc/test.py")).read().split("import yfinance")[0]
exec(src)                                      # -> F (FOMC sprendimų datos)
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
L = lambda t: pd.read_csv(f"{R}/59_ibs/data/{t}.csv", index_col=0, parse_dates=True).Close
bil = L("BIL").pct_change()
def st(x, a, b):
    x = x[a:b]; e = (1 + x).cumprod(); n = len(x) / 252; return f"{(e.iloc[-1] ** (1 / n) - 1) * 100:+5.1f}% kr {(e / e.cummax() - 1).min() * 100:3.0f}%"
PER = [("1994", "2012"), ("2013", "2019"), ("2020", "2026")]
for t in ("SPY", "TLT"):
    c = L(t); c = c[c.index >= "1994-01-01"]; r = c.pct_change().fillna(0); cash = bil.reindex(c.index).fillna(0.0001)
    fomc = pd.Series(c.index.isin(pd.DatetimeIndex(F)), c.index)
    nfp = pd.Series(False, c.index)
    for (y, m), g in c.groupby([c.index.year, c.index.month]):
        fr = g.index[g.index.day_of_week == 4]
        if len(fr): nfp[fr[0]] = True
    ann = fomc | nfp
    print(f"\n{t}: vid. dienos grąža bp (1994–2012 | 2013–19 | 2020–26)")
    for nm, m in (("FOMC dienos", fomc), ("NFP penktadieniai", nfp), ("paskelbimo dienos (abi)", ann), ("kitos dienos", ~ann)):
        print(f"  {nm:24s} " + " | ".join(f"{r[m][a:b].mean()*1e4:+5.1f} (n={m[a:b].sum()})" for a, b in PER))
    print(f"  {'laikyti':24s} " + " | ".join(st(r, a, b) for a, b in PER))
    for k in (1, 3):
        pos = ann.astype(float); rr = k * r - (k - 1) * cash
        x = pos * rr + (1 - pos) * cash - pos.diff().abs().fillna(0) * 0.0003
        print(f"  {'tik paskelbimo d., ' + str(k) + 'x':24s} " + " | ".join(st(x, a, b) for a, b in PER) + f" | rinkoje {pos.mean()*100:.0f}%")
