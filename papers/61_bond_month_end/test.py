"""61: Obligacijų mėnesio pabaigos efektas (Quantpedia „Month-End Effect in Treasuries“; indeksų trukmės pratęsimas paskutinę mėnesio dieną).
Laikyti TLT/IEF paskutines N prekybos dienų (įeinama uždarymu prieš N d.), likusį laiką BIL; papildomai – trumpinti/vengti pirmų mėnesio dienų.
Kaštai 0,03 %/sandorį. Yahoo duomenys (papers/59_ibs/data). Paleisti: quantconnect-lean/.venv/bin/python papers/61_bond_month_end/test.py"""
import os, numpy as np, pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); DD = os.path.join(os.path.dirname(D), "59_ibs/data"); FEE = 0.0003
L = lambda t: pd.read_csv(f"{DD}/{t}.csv", index_col=0, parse_dates=True).Close
bil = L("BIL").pct_change()
def st(x, a, b):
    x = x[a:b].dropna(); e = (1 + x).cumprod(); y = len(x) / 252
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+5.1f}% kr {(e / e.cummax() - 1).min() * 100:3.0f}%"
PER = [("2003", "2012"), ("2013", "2019"), ("2020", "2026")]
print("periodai: 2003–12 | 2013–19 | 2020–26")
for t in ("TLT", "IEF" if os.path.exists(f"{DD}/IEF.csv") else "TLT"):
    c = L(t); r = c.pct_change().fillna(0); cash = bil.reindex(c.index).fillna(0)
    idx = c.index; m = idx.to_period("M")
    left = pd.Series(idx, idx).groupby(m).transform(lambda s: np.arange(len(s))[::-1])   # 0 = paskutinė mėn. diena
    first = pd.Series(idx, idx).groupby(m).transform(lambda s: np.arange(len(s)))        # 0 = pirma mėn. diena
    print(f"\n{t} laikyti: " + " | ".join(st(r, a, b) for a, b in PER))
    # vidutinė grąža pagal dieną iki mėnesio galo
    print("  vid. dienos grąža (bp) pagal dieną iki mėn. galo (−5..−0) ir mėn. pradžią (+1..+3):")
    for lab, mask in [(f"−{k}", left == k) for k in range(5, -1, -1)] + [(f"+{k+1}", first == k) for k in range(3)]:
        print(f"    {lab:>3}: " + " | ".join(f"{r[mask][a:b].mean()*1e4:+5.1f}" for a, b in PER))
    for n in (1, 3, 5, 7):
        pos = (left < n).astype(float)                   # pozicija dieną d -> grąža dienos d (įeita vakar uždarymu)
        x = pos * r + (1 - pos) * cash - pos.diff().abs().fillna(0) * FEE
        print(f"  paskutinės {n} d.: " + " | ".join(st(x, a, b) for a, b in PER) + f" | rinkoje {pos.mean()*100:.0f}%")
    for n in (5,):
        pos = (left < n).astype(float) - (first < 3).astype(float)
        x = pos * r + (1 - pos.abs()) * cash - pos.diff().abs().fillna(0) * FEE
        print(f"  paskutinės {n} d. long + pirmos 3 d. short: " + " | ".join(st(x, a, b) for a, b in PER))
# 3x versija: TMF (etf-rotation duomenys, nuo 2009)
C = pd.read_csv(os.path.join(os.path.dirname(os.path.dirname(D)), "etf-rotation/data/close.csv"), index_col=0, parse_dates=True)
c = C.TMF.dropna(); r = c.pct_change().fillna(0); cash = bil.reindex(c.index).fillna(0); idx = c.index
left = pd.Series(idx, idx).groupby(idx.to_period("M")).transform(lambda s: np.arange(len(s))[::-1])
print(f"\nTMF laikyti: " + " | ".join(st(r, a, b) for a, b in PER))
for n in (3, 5, 7):
    pos = (left < n).astype(float); x = pos * r + (1 - pos) * cash - pos.diff().abs().fillna(0) * FEE
    print(f"  TMF paskutinės {n} d.: " + " | ".join(st(x, a, b) for a, b in PER) + f" | 2010–26 {st(x, '2010', '2027')}")
