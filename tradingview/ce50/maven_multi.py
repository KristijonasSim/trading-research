"""Mūsų atrinktos strategijos per Maven Omo 2-Step $10k ($38), 2025-01-01 .. 2026-11-08.
Kiekvienai: dienos pelnas % nuo pradinio balanso esant 1x (arba 1 % rizikos), dauginama iš sverto k.
Taisyklės kaip maven.py. Kripto: pelnas skaičiuojamas uždarymo dieną (atviri nuostoliai nematomi -> rezultatas per geras)."""
import json, zipfile
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).parent; FT = HERE.parents[1] / "freqtrade/results/maven"
SIZE, FEE, A, B = 10000, 38, "2025-01-01", "2026-11-08"
days = pd.bdate_range(A, B)


def daily(s):
    return s.groupby(s.index.normalize()).sum().reindex(days, fill_value=0.0)


src = {}
ce = pd.read_csv(HERE / "trades_signal_960.csv", index_col=0, parse_dates=True)
src["CE50 (long+short), 1 % rizika"] = daily(ce.R)
nb = pd.read_csv(HERE / "noise_trades.csv", parse_dates=["day"]).set_index("day")
src["Noise Breakout NAS100, 1x"] = daily(nb.ret * 100)
for d in sorted(FT.glob("*/")):
    z = sorted(d.glob("backtest-result-*.zip"))
    if not z: continue
    with zipfile.ZipFile(z[-1]) as f:
        j = json.load(f.open([n for n in f.namelist() if n.endswith(".json") and "config" not in n and "meta" not in n][0]))
    tr = pd.DataFrame(next(iter(j["strategy"].values()))["trades"])
    tr["close_date"] = pd.to_datetime(tr.close_date).dt.tz_localize(None)
    s = pd.Series(tr.profit_abs.values / 1000 * 100, index=tr.close_date)  # % nuo 1000 USDT
    # savaitgalio pelnas priskiriamas pirmadieniui
    s.index = s.index.normalize() + pd.offsets.BDay(0)
    src[f"{d.name} (kripto), 1x"] = daily(s)


def run(pnl):
    acc, phase, bal, pdays, start, pays, paid, funded = 1, 1, 0.0, 0, None, 0, 0.0, 0
    for d, p in pnl.items():
        if p == 0: continue
        if p <= -4: bal = -99
        bal += p
        if p >= 0.5: pdays += 1
        if bal <= -8:
            acc += 1; phase, bal, pdays, pays = 1, 0.0, 0, 0; continue
        if phase == 1 and bal >= 6 and pdays >= 3: phase, bal, pdays = 2, 0.0, 0
        elif phase == 2 and bal >= 8 and pdays >= 3: funded += 1; phase, bal, pdays, start = 3, 0.0, 0, d
        elif phase == 3 and np.busday_count(start.date(), d.date()) >= 10 and bal > 0 and pdays >= 3:
            pays += 1; paid += 0.8 * bal / 100 * SIZE + (FEE if pays == 3 else 0); bal, pdays, start = 0.0, 0, d
    return acc, funded, paid


months = len(days) / 21.7
out = [f"Maven Omo 2-Step $10k, {A}..{B} ({months:.0f} mėn.). k = svertas (CE50: rizika % sandoriui)."]
best = []
names = [n for n in src if n != "Noise + CE50 kartu"]
for name in names + ["Noise + CE50 kartu"]:
    out.append(f"\n{name}:")
    for k in (1, 2, 3, 4, 5, 6, 8, 10):
        if name == "Noise + CE50 kartu":
            pnl = src["Noise Breakout NAS100, 1x"] * k + src["CE50 (long+short), 1 % rizika"] * min(k / 2, 2)
        else:
            pnl = src[name] * k
        acc, f, paid = run(pnl)
        net = paid - acc * FEE
        out.append(f"  k={k:2}: sąskaitų {acc:3}, funded {f:2} ({f / months:.2f}/mėn.), išmokėta {paid:6.0f} $, grynai {net:6.0f} $")
        best.append((f / months, net, name, k))
out.append("\nDaugiausia funded per mėnesį:")
for fm, net, name, k in sorted(best, reverse=True)[:6]:
    out.append(f"  {name}, k={k}: {fm:.2f}/mėn., grynai {net:.0f} $")
print("\n".join(out)); (HERE / "REZ_MAVEN_MULTI.txt").write_text("\n".join(out))
