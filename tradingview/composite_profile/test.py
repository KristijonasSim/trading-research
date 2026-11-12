"""Instagram kestradess: 8 sesijų „composite“ profilis. Storos zonos (HVN) -> kaina stringa, plonos (LVN) -> greitai bėga iki kitos storos.
NAS100 5 min. RTH, 2019-2026. Profilis = kiek laiko kaina buvo kiekviename lygyje per 8 ankstesnes sesijas (laikas, ne apyvarta:
CFD apyvarta netikra; įraše irgi „kur rinka praleido laiką“). Lygis = 0,1 % kainos.
1) Ar plonose zonose kaina per 30 min. pajuda daugiau nei storose?
2) Prekyba: kaina iš storos zonos įeina į ploną -> sekti kryptį, tikslas kita stora zona, stop - stora zona, iš kurios išėjo."""
from pathlib import Path
import numpy as np, pandas as pd

D = Path(__file__).resolve().parents[1] / "ovn_box/data"
COST = 0.0001
df = pd.concat(pd.read_csv(f, index_col=0, parse_dates=True) for f in sorted(D.glob("NAS100_*.csv")))
df = df[~df.index.duplicated()].sort_index(); df.index = df.index.tz_convert("America/New_York")
m = df.index.hour * 60 + df.index.minute
df = df[(m >= 570) & (m < 960)]
days = [g for _, g in df.groupby(df.index.date) if len(g) >= 70]
BIN = 0.001
FAT, THIN = 1.0, 0.35

obs, trades = [], []
for i in range(8, len(days)):
    comp = pd.concat(days[i - 8:i]); g = days[i]
    ref = comp.close.iloc[-1]; w = ref * BIN
    lo0 = comp.low.min()
    nb = int((comp.high.max() - lo0) / w) + 1
    hist = np.zeros(nb)
    for h, l in zip(comp.high.values, comp.low.values):
        a, b = int((l - lo0) / w), int((h - lo0) / w)
        hist[a:b + 1] += 1.0 / (b - a + 1)
    dens = hist / hist.mean()

    def dn(p):
        k = int((p - lo0) / w)
        return dens[k] if 0 <= k < nb else -1.0

    c, h, l = g.close.values, g.high.values, g.low.values
    dd = np.array([dn(p) for p in c])
    for j in range(len(g) - 6):
        obs.append((dd[j], abs(c[j + 6] / c[j] - 1), (h[j + 1:j + 7].max() - l[j + 1:j + 7].min()) / c[j], g.index[j].year))
    # prekyba: perėjimas stora -> plona
    for j in range(1, len(g) - 6):
        if not (dd[j - 1] >= FAT and 0 <= dd[j] <= THIN): continue
        side = 1 if c[j] > c[j - 1] else -1
        k0 = int((c[j] - lo0) / w); k = k0
        while 0 <= k < nb and dens[k] < FAT: k += side
        if not (0 <= k < nb): continue
        target = lo0 + (k + (0 if side > 0 else 1)) * w
        stop = c[j - 1]
        R = abs(c[j] - stop)
        if R <= 0 or abs(target - c[j]) <= 0: continue
        ex = c[-1]
        for t in range(j + 1, len(g)):
            if (side > 0 and l[t] <= stop) or (side < 0 and h[t] >= stop): ex = stop; break
            if (side > 0 and h[t] >= target) or (side < 0 and l[t] <= target): ex = target; break
        trades.append((g.index[j], side * (ex / c[j] - 1) - COST, (side * (ex - c[j]) - COST * c[j]) / R, abs(target - c[j]) / R))
        break  # vienas sandoris per dieną

o = pd.DataFrame(obs, columns=["dens", "move", "rng", "y"])
o["zona"] = pd.cut(o.dens, [-2, -0.5, 0.35, 0.7, 1.0, 1.5, 100], labels=["už profilio", "plona <0,35", "0,35-0,7", "0,7-1", "1-1,5", "stora >1,5"])
out = ["1) Kiek kaina pajuda per 30 min. (bp = 0,01 %), pagal zoną:"]
out.append(o.groupby("zona", observed=True).agg(n=("move", "size"), judesys=("move", lambda x: 1e4 * x.mean()), rėžis=("rng", lambda x: 1e4 * x.mean())).round(1).to_string())
for a, b in ((2019, 2022), (2023, 2026)):
    s = o[(o.y >= a) & (o.y <= b)].groupby("zona", observed=True).move.mean() * 1e4
    out.append(f"  {a}-{b}: " + ", ".join(f"{k} {v:.1f}" for k, v in s.items()))
t = pd.DataFrame(trades, columns=["t", "ret", "R", "tgtR"]).set_index("t")
out.append(f"\n2) Prekyba stora->plona, sekti kryptį: {len(t)} sandorių, laimi {100 * (t.ret > 0).mean():.0f} %, "
           f"vid. {1e4 * t.ret.mean():+.1f} bp ({t.R.mean():+.3f} R), tikslas vid. {t.tgtR.median():.1f} R")
for a, b in (("2019", "2022"), ("2023", "2026")):
    s = t[a:b]; out.append(f"  {a}-{b}: {len(s)} sand., vid. {1e4 * s.ret.mean():+.1f} bp, {s.R.mean():+.3f} R")
print("\n".join(out)); (Path(__file__).parent / "REZULTATAI.txt").write_text("\n".join(out))
