"""98: Shillerio CAPE rinkos laikas (Campbell, Shiller 1998; „Excess CAPE Yield“ Shiller ir kt. 2020). Mėnesiniai Shiller duomenys 1881–2023:
nominali akcijų bendra grąža (P + D/12), obligacijų alternatyva – GS10 pajamingumas / 12 (apytiksliai). Signalas be ateities: CAPE lyginamas su
iki tol buvusia (plečiamo lango) mediana arba 20 m. slenkančiu vidurkiu. Taisyklės: akcijos kai CAPE < mediana (kitaip obligacijos); ECY = 1/CAPE − GS10 > 0.
Paleisti: quantconnect-lean/.venv/bin/python papers/98_cape/test.py"""
import os, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
D = os.path.dirname(os.path.abspath(__file__))
d = pd.read_excel(f"{D}/data/ie_data.xls", sheet_name="Data", header=7)
d = d[pd.to_numeric(d.Date, errors="coerce").notna()].copy(); d["Date"] = d.Date.astype(float)
for c in ("P", "D", "CAPE", "Rate GS10"): d[c] = pd.to_numeric(d[c], errors="coerce")
d = d.dropna(subset=["P"]); d["D"] = d.D.ffill()
r_eq = (d.P.shift(-1) + d.D / 12) / d.P - 1; r_b = d["Rate GS10"] / 1200
cape = d.CAPE; ecy = 1 / cape - d["Rate GS10"] / 100
yr = d.Date.astype(int)
def st(x, a, b):
    m = (yr >= a) & (yr <= b); x = x[m].dropna(); e = (1 + x).cumprod(); y = len(x) / 12; return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+5.1f}% kr {(e / e.cummax() - 1).min() * 100:3.0f}%"
PER = [(1901, 1950), (1951, 1990), (1991, 2023)]
print("periodai: 1901–50 | 1951–90 | 1991–2023 (CAPE paskelbtas 1988/1998)")
print(f"{'akcijos (bendra grąža)':36s} " + " | ".join(st(r_eq, a, b) for a, b in PER))
print(f"{'obligacijos (GS10/12)':36s} " + " | ".join(st(r_b, a, b) for a, b in PER))
for nm, sig in (("CAPE < plečiamo lango mediana", cape < cape.expanding(120).median()),
                ("CAPE < 20 m. vidurkis", cape < cape.rolling(240).mean()),
                ("CAPE < 20 m. vidurkis × 1,2", cape < 1.2 * cape.rolling(240).mean()),
                ("ECY > 0", ecy > 0), ("ECY > 2 %", ecy > 0.02)):
    s = sig.astype(float).shift(0)                      # signalas mėnesio t pabaigoje -> grąža t..t+1
    x = s * r_eq + (1 - s) * r_b
    print(f"{nm:36s} " + " | ".join(st(x, a, b) for a, b in PER) + f" | akcijose {s[yr >= 1901].mean()*100:.0f}%")
