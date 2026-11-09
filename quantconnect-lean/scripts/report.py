#!/usr/bin/env python3
"""results/raw/*/summary.json -> ../results/quantconnect_ranking.md + CSV"""
import json
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "results"
FX = {"02", "04", "08", "17", "1031", "270"}


def spy_hold():
    df = pd.read_csv(ROOT / "raw/daily/SPY.csv", index_col=0, parse_dates=True)["Close"]
    s = df["2021-11-08":"2026-11-07"]
    eq = s / s.iloc[0] * 1000
    yearly, prev = {}, 1000.0
    for y, g in eq.groupby(eq.index.year):
        yearly[str(y)] = round((g.iloc[-1] / prev - 1) * 100, 1); prev = g.iloc[-1]
    yrs = 5 / 1.0
    return {"final": round(eq.iloc[-1]), "cagr": round(((eq.iloc[-1] / 1000) ** (1 / 5) - 1) * 100, 1),
            "dd": round(-(eq / eq.cummax() - 1).min() * 100, 1), "yearly": yearly}


def main():
    rows = [json.loads(f.read_text()) for f in (ROOT / "results/raw").glob("*/summary.json")]
    df = pd.DataFrame(rows)
    years = sorted({y for r in rows for y in r["yearly_pct"]})
    for y in years:
        df[y] = df["yearly_pct"].apply(lambda d, y=y: d.get(y))
    df["name"] = df["strategy"].str.split(" ", n=1).str[1]
    df["market"] = df["strategy"].str.split(" ").str[0].map(lambda n: "forex" if n in FX else ("forumas" if n.startswith("F") else "akcijos/ETF"))
    df.drop(columns=["yearly_pct"]).sort_values("cagr_pct", ascending=False).to_csv(OUT / "quantconnect_all_results.csv", index=False)
    bh = spy_hold()
    md = ["# QuantConnect strategijų rezultatai", "",
          "Variklis: QuantConnect Lean (Docker, lokaliai). Laikotarpis 2021-11-08 – 2026-11-08, mokestis 0,1 % nuo sandorio, "
          "rezultatai perskaičiuoti į 1000 pradžią. Dienos kainos: Yahoo (su dividendais), valandinės: Dukascopy.", "",
          f"**Pirkti ir laikyti SPY (S&P 500):** {bh['cagr']}%/m., iš 1000 liktų {bh['final']} (max kritimas {bh['dd']}%) — "
          + " | ".join(f"{y}: {bh['yearly'].get(y)}%" for y in years), "",
          "Forex strategijas lyginti su 0 % (grynieji), nes valiutų „pirkti ir laikyti“ neturi prasmės.", ""]
    cols = ["name", "variant", "resolution", "cagr_pct", *years, "final_usdt", "max_drawdown_pct", "trades"]
    for m in ["akcijos/ETF", "forumas", "forex"]:
        sub = df[df.market == m].sort_values("cagr_pct", ascending=False)
        if len(sub):
            md += [f"## {m}", "", sub[cols].to_markdown(index=False), ""]
    errs = sorted(d.name for d in (ROOT / "results/raw").iterdir() if (d / "error.txt").exists())
    zero = df[(df.trades == 0)]
    if len(zero):
        md += ["## Neatliko nė vieno sandorio", "",
               "Dažniausia priežastis: strategija prekiauja dienos viduryje ir tikrina minutines/valandines kainas, "
               "kurių šiems ETF neturime (reikėtų IBKR duomenų).", ""] + [f"- {r.strategy} {r.variant} {r.resolution}" for r in zero.itertuples()] + [""]
    if errs:
        md += ["## Nepavyko paleisti", ""] + [f"- {e}" for e in errs]
    (OUT / "quantconnect_ranking.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
