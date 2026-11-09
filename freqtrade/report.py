#!/usr/bin/env python3
"""Collects results/raw/*/summary.json into ranking tables (CSV + Markdown)."""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "results/raw"
OUT = ROOT.parent / "results"
DATA = ROOT / "user_data/data/binance"
START, END = "2021-11-08", "2026-11-08"

from run_all import GROUPS  # noqa: E402

GROUP_LABEL = {"btc_eth": "BTC+ETH", "alts10": "Top 10 alts"}


def buy_and_hold(pairs):
    """Equal-weight buy & hold: yearly % and CAGR."""
    closes = {}
    for p in pairs:
        f = DATA / f"{p.replace('/', '_')}-1d.feather"
        if not f.exists():
            continue
        df = pd.read_feather(f).set_index("date")["close"]
        df.index = df.index.tz_localize(None)
        closes[p] = df[START:END]
    if not closes:
        return None
    px = pd.DataFrame(closes).dropna()
    equity = (px / px.iloc[0]).mean(axis=1) * 1000
    yearly = {}
    prev = equity.iloc[0]
    for y, s in equity.groupby(equity.index.year):
        yearly[str(y)] = round((s.iloc[-1] / prev - 1) * 100, 1)
        prev = s.iloc[-1]
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr = (equity.iloc[-1] / 1000) ** (1 / years) - 1
    dd = (equity / equity.cummax() - 1).min()
    return {"cagr_pct": round(cagr * 100, 1), "yearly_pct": yearly,
            "max_drawdown_pct": round(-dd * 100, 1)}


def main():
    rows = [json.loads(f.read_text()) for f in RAW.glob("*/summary.json")]
    failed = sorted(d.name for d in RAW.iterdir() if (d / "error.txt").exists()) if RAW.exists() else []
    if not rows:
        print("no results yet")
        return
    df = pd.DataFrame(rows)
    years = sorted({y for r in rows for y in r["yearly_pct"]})
    for y in years:
        df[y] = df["yearly_pct"].apply(lambda d, y=y: d.get(y))
    df = df.drop(columns=["yearly_pct"])
    df["avg_year_pct"] = (df[years].sum(axis=1) / 5).round(1)  # simple average: sum of yearly % / 5 years
    OUT.mkdir(exist_ok=True)
    df.sort_values(["group", "cagr_pct"], ascending=[True, False]).to_csv(
        OUT / "freqtrade_all_results.csv", index=False)

    cols = ["strategy", "mode", "style", "timeframe", "cagr_pct", *years,
            "avg_year_pct", "total_return_pct",
            "max_drawdown_pct", "trades_per_year", "win_rate_pct", "avg_trade_hours"]
    md = ["# Freqtrade strategijų rezultatai", "",
          f"Laikotarpis: {START} – {END} (5 m.), Binance, mokestis 0.1% spot / 0.05% futures, "
          "pradinis balansas 1000 USDT.",
          "2021 ir 2026 metai yra daliniai (lapkr.–gruod. ir saus.–lapkr.).", ""]
    for g, pairs in GROUPS.items():
        sub = df[df.group == g].sort_values("cagr_pct", ascending=False)
        if sub.empty:
            continue
        bh = buy_and_hold(pairs)
        md += [f"## {GROUP_LABEL[g]} ({', '.join(p.split('/')[0] for p in pairs)})", ""]
        if bh:
            yrs = " | ".join(f"{y}: {bh['yearly_pct'].get(y, '-')}%" for y in years)
            md += [f"**Pirkti ir laikyti:** {bh['cagr_pct']}%/m. (max kritimas "
                   f"{bh['max_drawdown_pct']}%) — {yrs}", ""]
            sub = sub.assign(beats_hold=sub["cagr_pct"] > bh["cagr_pct"])
        md += [sub[cols + (["beats_hold"] if bh else [])].to_markdown(index=False), ""]
    if failed:
        md += ["## Nepavykę paleisti", "", *[f"- {f}" for f in failed], ""]
    (OUT / "freqtrade_ranking.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
