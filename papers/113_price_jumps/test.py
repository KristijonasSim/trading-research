"""113: Kainų šuoliai (Caporale, Plastun 2019). Šuolis = dienos grąža > k * 30 d. std. Kitą dieną (atidarymas = vakar
uždarymas) laikoma 1 arba 3 d. kryptimi „tęsti“ arba „atšokti“. Visata: top 10 pagal 30 d. apyvartą (su išregistruotomis),
lygios dalys tarp aktyvių signalų, max 10 pozicijų po 10 %. Mokestis 0,1 % ratui. 2018–2021-11 / 2021-11–2026-11."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, pandas as pd
from xsec import load
FEE = 0.001
P, V = load(); R = P.pct_change(fill_method=None)
sd = R.rolling(30, min_periods=25).std().shift(1)
liq = V.rolling(30, min_periods=20).mean(); age = P.notna().cumsum()
rank = liq.where(age >= 60).rank(axis=1, ascending=False)
def run(k, mode, hold, side, a, b, topn=10):
    z = R / sd
    sig = pd.DataFrame(0.0, index=R.index, columns=R.columns)
    up, dn = (z > k) & (rank <= topn), (z < -k) & (rank <= topn)
    d = 1 if mode == "tęsti" else -1
    sig[up] = d; sig[dn] = -d
    if side == "long": sig = sig.clip(lower=0)
    pos = sum(sig.shift(j) for j in range(1, hold + 1)).clip(-1, 1)  # pozicija nuo kitos dienos
    w = pos * 0.1
    gross = (w * R).sum(axis=1); turn = w.diff().abs().sum(axis=1)
    ret = (gross - turn * FEE)[(R.index >= a) & (R.index < b)]
    eq = (1 + ret).cumprod(); yrs = (pd.Timestamp(b) - pd.Timestamp(a)).days / 365.25
    n = int((sig[(sig.index >= a) & (sig.index < b)] != 0).sum().sum())
    return (eq.iloc[-1] ** (1 / yrs) - 1) * 100, ((eq / eq.cummax()) - 1).min() * 100, n, ret.groupby(ret.index.year).apply(lambda x: (1 + x).prod() - 1).mul(100).round(0).astype(int).to_dict()
out = ["# 113 Kainų šuoliai – rezultatai\n", "| Laikotarpis | k | Kryptis | Laikyti d. | Pusė | %/m. | Kritimas | Signalai | Metai |", "|---|---|---|---|---|---|---|---|---|"]
for a, b in [("2018-01-01", "2021-11-08"), ("2021-11-08", "2026-11-08")]:
    for k in [2, 3]:
        for mode in ["tęsti", "atšokti"]:
            for hold in [1, 3]:
                for side in ["long", "long+short"]:
                    r = run(k, mode, hold, side, a, b)
                    out.append(f"| {a[:7]}–{b[:7]} | {k} | {mode} | {hold} | {side} | {r[0]:+.1f} | {r[1]:.0f} % | {r[2]} | {r[3]} |")
open("rezultatai_raw.md", "w").write("\n".join(out) + "\n"); print("\n".join(out))
