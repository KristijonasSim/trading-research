#!/usr/bin/env python3
"""Collect results/raw/*/summary.json into results/octobot_ranking.md + CSV (same layout as freqtrade report)."""
import json, sqlite3, datetime as dt
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results/raw"
OUT = ROOT.parent / "results"
START_TS, END_TS = 1636329600, 1794096000
GROUPS = {"btc_eth": "BTC+ETH", "alts10": "Top 10 alts", "us30": "US30 (Dow Jones)", "nas100": "NAS100", "spx500": "S&P 500", "xau": "Auksas (XAU)"}
NAMES = {"daily_trading": "Daily Trading", "dip_analyser": "Dip Analyser", "grid_trading": "Grid",
         "trailing_grid_trading": "Trailing Grid", "index_trading": "Index (rebalance)",
         "smart_dca": "Smart DCA", "staggered_orders_trading": "Staggered Orders", "simple_dca": "Simple DCA"}


def buy_and_hold(group):
    f = ROOT / f"backtesting/data/{group}.data"
    if not f.exists():
        return None
    con = sqlite3.connect(f)
    closes = {}
    for sym, c in con.execute("select symbol, candle from ohlcv where time_frame='1d'"):
        c = json.loads(c)
        if START_TS <= c[0] < END_TS:
            closes.setdefault(sym, {})[pd.Timestamp(c[0], unit="s")] = c[4]
    px = pd.DataFrame(closes).sort_index().dropna()
    eq = (px / px.iloc[0]).mean(axis=1) * 1000
    yearly, prev = {}, eq.iloc[0]
    for y, s in eq.groupby(eq.index.year):
        yearly[str(y)] = round((s.iloc[-1] / prev - 1) * 100, 1)
        prev = s.iloc[-1]
    years = (END_TS - START_TS) / 86400 / 365.25
    return {"cagr_pct": round(((eq.iloc[-1] / 1000) ** (1 / years) - 1) * 100, 1), "yearly_pct": yearly,
            "max_drawdown_pct": round(-(eq / eq.cummax() - 1).min() * 100, 1), "final": round(eq.iloc[-1])}


def main():
    rows = [json.loads(f.read_text()) for f in RAW.glob("*/summary.json")]
    df = pd.DataFrame(rows)
    years = sorted({y for r in rows for y in r["yearly_pct"]})
    for y in years:
        df[y] = df["yearly_pct"].apply(lambda d, y=y: d.get(y))
    def nice(n):
        if "+" in n:
            ev = n.split("+")[1].replace("Evaluator", "")
            return f"Daily Trading: {ev}"
        return NAMES.get(n, n)
    df["bot"] = df["strategy"].map(nice)
    NAMES["market_making"] = "Market Making"
    df.drop(columns=["yearly_pct", "end_holdings"]).sort_values(["group", "cagr_pct"], ascending=[True, False]) \
        .to_csv(OUT / "octobot_all_results.csv", index=False)
    cols = ["bot", "cagr_pct", *years, "total_return_pct", "final_usdt", "max_drawdown_pct", "trades_per_year"]
    md = ["# OctoBot strategijų rezultatai", "",
          "Variklis: OctoBot 2.1.1 backtesteris. Laikotarpis 2021-11-08 – 2026-11-08, Binance spot, "
          "mokestis 0,1 %, pradžia 1000 USDT. Grąža skaičiuojama pagal visą portfelio vertę kiekvienos dienos pabaigoje.", ""]
    for g, label in GROUPS.items():
        sub = df[df.group == g].sort_values("cagr_pct", ascending=False)
        if sub.empty:
            continue
        bh = buy_and_hold(g)
        md += [f"## {label}", ""]
        if bh:
            md += [f"**Pirkti ir laikyti:** {bh['cagr_pct']}%/m., iš 1000 liktų {bh['final']} (max kritimas "
                   f"{bh['max_drawdown_pct']}%) — " + " | ".join(f"{y}: {bh['yearly_pct'].get(y)}%" for y in years), ""]
            sub = sub.assign(beats_hold=sub["cagr_pct"] > bh["cagr_pct"])
        md += [sub[cols + (["beats_hold"] if bh else [])].to_markdown(index=False), ""]
    errs = sorted(d.name for d in RAW.iterdir() if (d / "error.txt").exists())
    if errs:
        md += ["## Nepavyko", ""] + [f"- {e}" for e in errs]
    (OUT / "octobot_ranking.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
