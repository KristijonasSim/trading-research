"""day-trader-skill (Jakeschincariol, Instagram itstundeanthony): ORB taisyklė iš README.
15 min. rėžis (9:30-9:45), long kai 5 min. žvakė užsidaro virš rėžio max (iki 15:30),
įėjimas kitos žvakės atidarymu, stop = rėžio vidurys, tikslas = 1R, uždaryti 15:55."""
import sys
from pathlib import Path
import numpy as np, pandas as pd

D = Path(sys.argv[1]); COST = 0.0004  # 0,02 % slydimas į kiekvieną pusę
rows = []
for f in sorted(D.glob("*.csv")):
    df = pd.read_csv(f, index_col=0, parse_dates=True)
    df.index = df.index.tz_convert("America/New_York")
    t = df.index.hour * 60 + df.index.minute
    df = df[(t >= 570) & (t < 960)]
    for day, g in df.groupby(df.index.date):
        tm = g.index.hour * 60 + g.index.minute
        if len(g) < 70 or tm[0] != 570:
            continue
        o, h, l, c = g.open.values, g.high.values, g.low.values, g.close.values
        orh, orl = h[:3].max(), l[:3].min(); mid = (orh + orl) / 2
        sig = [j for j in range(3, len(g) - 1) if tm[j] <= 925 and c[j] > orh]
        if not sig:
            continue
        j = sig[0] + 1; e = o[j]; risk = e - mid
        if risk <= 0:
            continue
        tp, ex = e + risk, None
        for k in range(j, len(g)):
            if l[k] <= mid: ex = min(mid, o[k]); break  # stop (jei abu toje pačioje žvakėje - stop)
            if h[k] >= tp: ex = max(tp, o[k]); break
            if tm[k] >= 950: ex = c[k]; break
        if ex is None: ex = c[-1]
        rows.append(dict(sym=f.stem, day=pd.Timestamp(day), R=(ex - e) / risk, ret=ex / e - 1 - COST,
                         Rnet=(ex - e - COST * e) / risk))

r = pd.DataFrame(rows); r["y"] = r.day.dt.year
out = [f"Sandorių: {len(r)}, akcijų: {r.sym.nunique()}, {r.day.min():%Y-%m}..{r.day.max():%Y-%m}",
       f"Laimi: {100 * (r.ret > 0).mean():.1f} %",
       f"Vid. sandoris: {r.R.mean():+.3f} R be kaštų, {r.Rnet.mean():+.3f} R su kaštais, {100 * r.ret.mean():+.3f} % kainos",
       "", "Pagal metus (vid. R su kaštais, laimi %):"]
y = r.groupby("y").agg(n=("R", "size"), R=("Rnet", "mean"), win=("ret", lambda x: (x > 0).mean()))
out.append(y.round(3).to_string())
s = r.groupby("sym").Rnet.mean().sort_values()
out += ["", f"Akcijos su teigiamu vid. R: {(s > 0).sum()} iš {len(s)}", s.round(3).to_string()]
print("\n".join(out)); Path(sys.argv[2]).write_text("\n".join(out))
