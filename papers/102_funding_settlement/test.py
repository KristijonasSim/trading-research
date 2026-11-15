"""102: kainos elgsena aplink funding atsiskaitymą (00/08/16 UTC), Binance perp 5m, 12 monetų.
Walk-forward: šablonas (kuriuo 5 min. intervalu pirkti/parduoti) parenkamas 2021-11–2023, tikrinamas 2024–2026.
Mokestis 0,05 % į pusę (0,1 % ratas)."""
import pandas as pd, numpy as np, glob, os
D = os.path.expanduser("~/Desktop/trading-research/freqtrade/user_data/data/binance/futures")
FEE = 0.001
rows = []
for f in sorted(glob.glob(f"{D}/*_USDT_USDT-5m-futures.feather")):
    c = os.path.basename(f).split("_")[0]
    df = pd.read_feather(f)[["date", "open", "close"]].set_index("date")
    r = np.log(df["close"]).diff()
    df["r"] = r
    df["min"] = df.index.hour * 60 + df.index.minute
    df["coin"] = c
    rows.append(df)
a = pd.concat(rows)
a["phase"] = a["min"] % 480  # minutės nuo paskutinio funding
train = a[a.index < "2024-01-01"]; test = a[a.index >= "2024-01-01"]
prof_tr = train.groupby("phase")["r"].mean() * 1e4
prof_te = test.groupby("phase")["r"].mean() * 1e4
out = ["# 102 Funding atsiskaitymo efektas (Binance perp, 12 monetų, 5m)\n",
       "Vidutinė 5 min. grąža (bazės punktais) pagal laiką nuo funding (00/08/16 UTC):\n",
       "| min. nuo funding | 2021-11–2023 | 2024–2026 |", "|---|---|---|"]
for p in list(range(0, 60, 5)) + list(range(420, 480, 5)):
    out.append(f"| {p if p < 240 else p - 480} | {prof_tr[p]:+.2f} | {prof_te[p]:+.2f} |")
# geriausias langas (iki 2 val.) treniruotėje -> testas
best = None
for start in range(0, 480, 5):
    for L in range(1, 25):
        idx = [(start + 5 * k) % 480 for k in range(L)]
        s = prof_tr[idx].sum()
        if best is None or abs(s) > abs(best[2]): best = (start, L, s)
start, L, s = best
idx = [(start + 5 * k) % 480 for k in range(L)]
side = np.sign(s)
def stats(x):
    w = x[x["phase"].isin(idx)].copy()
    w["day"] = (w.index - pd.Timedelta(minutes=start)).floor("480min")
    g = w.groupby(["coin", "day"])["r"].sum() * side - FEE
    per = g.groupby(level=1).mean()
    yrs = (per.index[-1] - per.index[0]).days / 365.25
    return per.mean() * 1e4, (np.exp(per.sum()) ** (1 / yrs) - 1) * 100, (per > 0).mean() * 100
tr = stats(train); te = stats(test)
out += ["", f"Geriausias langas treniruotėje: nuo {start} min. po funding, {L*5} min., {'long' if side>0 else 'short'} (be mokesčių {s:+.1f} bp).",
        f"- 2021-11–2023 su mokesčiais: {tr[0]:+.1f} bp/sandoriui, {tr[1]:+.1f} %/m., laimi {tr[2]:.0f} %",
        f"- 2024–2026 su mokesčiais: {te[0]:+.1f} bp/sandoriui, {te[1]:+.1f} %/m., laimi {te[2]:.0f} %"]
open("rezultatai_raw.md", "w").write("\n".join(out) + "\n"); print("\n".join(out[-4:]))
