"""CE50 tik long, visa sąskaita į 3x Nasdaq ETP (QQQ3/TQQQ). Grąža ≈ 3 x indekso judėjimas per sandorį, 0,1 % spread."""
import pandas as pd, numpy as np
from pathlib import Path
out = []
for em, lab in ((960, "uždaryti 16:00 (TQQQ, JAV birža)"), (690, "uždaryti 11:30 ET (QQQ3 LSE/Xetra uždarymas)")):
    t = pd.read_csv(Path(__file__).parent / f"trades_signal_{em}.csv", index_col=0, parse_dates=True)
    t = t[t.side > 0]
    r = 3 * t.pct - 0.001
    eq = (1 + r).cumprod(); y = (r.index[-1] - r.index[0]).days / 365.25
    out.append(f"{lab}: {len(t)} sandorių, laimi {100*(r>0).mean():.0f} %")
    for a, b, nm in (("2016", "2026", "viso 2016-26"), ("2016", "2021", "2016-21"), ("2022", "2026", "2022-26")):
        rr = r[a:b]; e = (1 + rr).cumprod(); yy = (rr.index[-1] - rr.index[0]).days / 365.25
        out.append(f"   {nm}: {100*(e.iloc[-1]**(1/yy)-1):+.1f} %/m., kritimas {100*(1-e/e.cummax()).max():.0f} %, blogiausia diena {100*rr.min():.1f} %")
    yr = r.groupby(r.index.year).apply(lambda x: 100 * ((1 + x).prod() - 1)).round(0)
    out.append("   metai: " + ", ".join(f"{k} {v:+.0f}%" for k, v in yr.items()))
print("\n".join(out)); (Path(__file__).parent / "REZ_QQQ3.txt").write_text("\n".join(out))
