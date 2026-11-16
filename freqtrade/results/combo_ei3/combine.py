"""Sujungia strategijų sandorius į dienos balanso kreives ir skaičiuoja portfelius su EI3v2.
Kiekviena strategija: 10 000 USDT, sudėtinis augimas; pelnas užskaitomas sandorio uždarymo dieną.
Portfelis: svoriai perbalansuojami kas mėnesį. Rezultatas -> results/combo/REZULTATAI.md"""
import json, zipfile, glob, itertools, os
import pandas as pd, numpy as np
D = os.path.dirname(os.path.abspath(__file__))
idx = pd.date_range("2020-01-01", "2026-11-08", freq="D")

def curve(name):
    z = glob.glob(f"{D}/{name}/*.zip")
    if not z: return None
    zf = zipfile.ZipFile(z[0]); n = [x for x in zf.namelist() if x.endswith(".json") and "config" not in x and "meta" not in x][0]
    t = list(json.loads(zf.read(n))["strategy"].values())[0]["trades"]
    if not t: return None
    s = pd.Series([x["profit_abs"] for x in t], pd.to_datetime([x["close_date"] for x in t]).tz_localize(None).normalize())
    bal = 10000 + s.groupby(level=0).sum().reindex(idx, fill_value=0).cumsum()
    return bal.pct_change().fillna(0)

def stats(r, a="2020-01-01", b="2026-11-08"):
    r = r[(r.index >= a) & (r.index < b)]; e = (1 + r).cumprod(); y = (r.index[-1] - r.index[0]).days / 365.25
    return (e.iloc[-1] ** (1 / y) - 1) * 100, (e / e.cummax() - 1).min() * 100

def port(rs, w):
    """Mėnesinis perbalansavimas: kiekvieno mėnesio pradžioje svoriai w; per mėnesį dalys dreifuoja."""
    out = []
    for m, g in pd.concat(rs, axis=1).groupby(pd.Grouper(freq="ME")):
        e = (1 + g).cumprod().mul(w, axis=1).sum(axis=1)
        out.append(e / e.shift(1).fillna(1) - 1)
    return pd.concat(out)

def yearly(r): return r.groupby(r.index.year).apply(lambda x: (1 + x).prod() - 1).mul(100).round(0).astype(int).to_dict()
def monthly26(r): return r[r.index >= "2026-01-01"].groupby(pd.Grouper(freq="ME")).apply(lambda x: (1 + x).prod() - 1).mul(100).round(1).tolist()

names = [os.path.basename(p) for p in glob.glob(f"{D}/*") if os.path.isdir(p) and not os.path.basename(p).startswith(("new_", "old_"))]
C = {n: c for n in names if (c := curve(n)) is not None}
out = ["# EI3v2 + kitos strategijos, 2020-01 – 2026-11 (dienos balansas pagal uždarytus sandorius)\n",
       "Pastaba: kritimas skaičiuojamas pagal uždarytus sandorius, todėl tikras (su atvirais sandoriais) didesnis.\n",
       "## Pavienės strategijos\n", "| Strategija | 2020–26 %/m. | kritimas | 2022–26 %/m. | kritimas | Metai | Mėn. be sandorių 2022–26 |", "|---|---|---|---|---|---|---|"]
for n, r in sorted(C.items()):
    c1, d1 = stats(r); c2, d2 = stats(r, "2022-01-01"); idle = int((r[r.index >= "2022-01-01"].groupby(pd.Grouper(freq="ME")).apply(lambda x: (x != 0).sum()) == 0).sum())
    out.append(f"| {n} | {c1:+.0f} | {d1:.0f} % | {c2:+.0f} | {d2:.0f} % | {yearly(r)} | {idle} |")
# koreliacija su EI3v2 (mėnesinės grąžos)
M = pd.DataFrame({n: r.groupby(pd.Grouper(freq="ME")).apply(lambda x: (1 + x).prod() - 1) for n, r in C.items()})
out += ["\n## Mėnesinių grąžų koreliacija su EI3F_L2 (mažesnė = geriau papildo)\n", "| Strategija | koreliacija |", "|---|---|"]
for n, v in M.corr()["EI3F_L2"].sort_values().items(): out.append(f"| {n} | {v:+.2f} |")
# portfeliai
res = []
for base in [b for b in ("EI3F_L2", "EI3F_L3") if b in C]:
    others = [n for n in C if not n.startswith("EI3F")]
    for k in (1, 2, 3):
        for combo in itertools.combinations(others, k):
            for wb in (0.5, 0.6, 0.7):
                w = [wb] + [(1 - wb) / k] * k
                r = port([C[base]] + [C[n] for n in combo], w)
                c1, d1 = stats(r); c2, d2 = stats(r, "2022-01-01"); c26, d26 = stats(r, "2026-01-01")
                res.append((c2 / max(-d2, 3), base, wb, combo, c1, d1, c2, d2, c26, r))
res.sort(key=lambda x: -x[0])
out += ["\n## Geriausi portfeliai (rikiuota pagal 2022–26 grąžą / kritimą)\n",
        "| Bazė | EI3 dalis | Kitos (po lygiai) | 2020–26 %/m. | kritimas | 2022–26 %/m. | kritimas | 2026 %/m. | Metai | 2026 mėn. |", "|---|---|---|---|---|---|---|---|---|---|"]
seen = set()
for x in res:
    key = (x[1], x[3])
    if key in seen: continue
    seen.add(key)
    out.append(f"| {x[1]} | {x[2]:.0%} | {', '.join(x[3])} | {x[4]:+.0f} | {x[5]:.0f} % | {x[6]:+.0f} | {x[7]:.0f} % | {x[8]:+.0f} | {yearly(x[9])} | {monthly26(x[9])} |")
    if len(seen) >= 25: break
for b in ("EI3F_L2", "EI3F_L3"):
    if b in C: r = C[b]; out.append(f"| {b} vienas | 100% | – | {stats(r)[0]:+.0f} | {stats(r)[1]:.0f} % | {stats(r,'2022-01-01')[0]:+.0f} | {stats(r,'2022-01-01')[1]:.0f} % | {stats(r,'2026-01-01')[0]:+.0f} | {yearly(r)} | {monthly26(r)} |")
open(f"{D}/REZULTATAI.md", "w").write("\n".join(out) + "\n"); print("\n".join(out[:60]))
