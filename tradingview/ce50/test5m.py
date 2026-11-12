"""Instagram cemarketsolutions: „CE 50% Model“ (žada 59,37 %/m. 2016-2026, ¼ Kelly).
8:30-9:30 ET rėžis, vidurys 50 %. Pirmoji 3 min. žvakė nuo 9:30 užsidaro žemiau vidurio -> short kitos žvakės atidarymu
(aukščiau -> long). Stop už rėžio, traukiamas prie kiekvieno patvirtinto 15 min. swing high (long - swing low). Uždaryti 16:00.
NAS100 1 min. (Dukascopy), 2016-2026."""
from pathlib import Path
import numpy as np, pandas as pd

D = Path(__file__).parent / "data1m"
import os
COST = float(os.environ.get("COST", "0.0001"))  # 0,01 % kainos už sandorį
EXIT_MIN = int(os.environ.get("EXIT_MIN", "960"))
MODE = os.environ.get("MODE", "signal")  # signal / random / long / short
RNG = np.random.default_rng(int(os.environ.get("SEED", "1")))
df = pd.concat(pd.read_csv(f, index_col=0, parse_dates=True) for f in sorted(D.glob("NAS100_*.csv")))
df = df[~df.index.duplicated()].sort_index(); df.index = df.index.tz_convert("America/New_York")
df["m"] = df.index.hour * 60 + df.index.minute
df = df[(df.m >= 510) & (df.m < 960)]

rows = []
for day, g in df.groupby(df.index.date):
    m = g.m.values
    rng = g[m < 570]; s = g[m >= 570]
    if len(rng) < 55 or len(s) < 380 or s.m.iloc[0] != 570:
        continue
    rh, rl = rng.high.max(), rng.low.min(); mid = (rh + rl) / 2
    c3 = s.close.iloc[4]
    if c3 == mid: continue
    side = -1 if c3 < mid else 1
    o, h, l, c, mm = s.open.values, s.high.values, s.low.values, s.close.values, s.m.values
    e = o[5]; stop = rh if side < 0 else rl; R = abs(e - stop)
    # palyginimui: kita kryptis, bet tas pats stop atstumas
    if MODE in ("random", "long", "short"):
        side = RNG.choice([-1, 1]) if MODE == "random" else (1 if MODE == "long" else -1)
        stop = e - side * R
    if R <= 0 or (side < 0 and e >= stop) or (side > 0 and e <= stop):
        continue
    # 15 min. žvakės nuo 9:30
    q = s.groupby((s.m - 570) // 15).agg(high=("high", "max"), low=("low", "min"))
    qh, ql = q.high.values, q.low.values
    ex = None
    for k in range(5, len(s)):
        if mm[k] >= EXIT_MIN: ex = o[k]; break
        # pivot j patvirtinamas uždarius j+1 žvakę, t. y. nuo minutės 570 + 15*(j+2)
        jq = (mm[k] - 570) // 15 - 2
        if jq >= 1 and (mm[k] - 570) % 15 == 0:
            if side < 0 and qh[jq] > qh[jq - 1] and qh[jq] > qh[jq + 1]: stop = min(stop, qh[jq])
            if side > 0 and ql[jq] < ql[jq - 1] and ql[jq] < ql[jq + 1]: stop = max(stop, ql[jq])
        if side < 0 and h[k] >= stop: ex = max(stop, o[k]); break
        if side > 0 and l[k] <= stop: ex = min(stop, o[k]); break
    if ex is None: ex = c[-1]
    rows.append(dict(day=pd.Timestamp(day), side=side, R=(side * (ex - e) - COST * e) / R, risk_pct=R / e, pct=side * (ex - e) / e))

t = pd.DataFrame(rows).set_index("day"); t["y"] = t.index.year


def grow(r, f):
    eq = (1 + f * r).cumprod(); y = (r.index[-1] - r.index[0]).days / 365.25
    return 100 * (eq.iloc[-1] ** (1 / y) - 1), 100 * (1 - eq / eq.cummax()).max()


tr, te = t[t.index < "2022-01-01"], t[t.index >= "2022-01-01"]
fs = np.linspace(0.001, 0.2, 400)
kelly = fs[np.argmax([np.log1p(np.maximum(f * tr.R, -0.999)).sum() for f in fs])]
out = [f"Sandorių: {len(t)} ({t.index[0]:%Y-%m}..{t.index[-1]:%Y-%m}), short {(t.side < 0).sum()}, long {(t.side > 0).sum()}",
       f"Laimi: {100 * (t.R > 0).mean():.1f} %, vid. {t.R.mean():+.3f} R, viso {t.R.sum():+.0f} R, didžiausias {t.R.max():.1f} R",
       f"Vid. rizika (stop atstumas): {100 * t.risk_pct.mean():.2f} % kainos",
       f"Short: vid. {t[t.side < 0].R.mean():+.3f} R | Long: vid. {t[t.side > 0].R.mean():+.3f} R", "", "Pagal metus (vid. R, suma R):"]
out.append(t.groupby("y").R.agg(["size", "mean", "sum"]).round(3).to_string())
out.append(f"\nKelly pagal 2016-21: {100 * kelly:.1f} % rizikos sandoriui, ¼ Kelly = {100 * kelly / 4:.2f} %")
for lab, part in (("2016-21 (mokymosi)", tr), ("2022-26 (nematyta)", te), ("viso", t)):
    g1, d1 = grow(part.R, 0.01); gk, dk = grow(part.R, kelly / 4)
    out.append(f"  {lab}: 1 % rizika -> {g1:+.1f} %/m. (kritimas {d1:.0f} %); ¼ Kelly -> {gk:+.1f} %/m. (kritimas {dk:.0f} %)")
for lab, part in (("tik short", t[t.side < 0]), ("tik long", t[t.side > 0])):
    if len(part) < 10: continue
    g1, d1 = grow(part.R, 0.01); out.append(f"  {lab}, 1 % rizika: {g1:+.1f} %/m. (kritimas {d1:.0f} %)")
t.to_csv(Path(__file__).parent / f"trades5m_{MODE}_{EXIT_MIN}.csv")
print("\n".join(out)); (Path(__file__).parent / f"REZ_{MODE}_{COST}.txt").write_text("\n".join(out))
