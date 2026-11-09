#!/usr/bin/env python3
"""
Out-of-sample check: the strategies selected on 2021-11-08..2026-11-08 are run on the unseen
period 2018-01-01..2021-11-08 with exactly the same config, pairs and fee.
Pairs that did not exist yet on Binance simply join when their data starts.

Usage: .venv/bin/python run_oos.py
Output: results/oos/<run>/ (raw) and ../results/oos_freqtrade.json
"""
import json
from pathlib import Path
import pandas as pd
import run_all as ra

TIMERANGE = "20180101-20211108"
RUNS = [  # strategy, group
    ("CombinedBinHAndCluc", "alts10"),
    ("CombinedBinHAndCluc", "btc_eth"),
    ("ReinforcedAverageStrategy", "alts10"),
    ("UniversalMACD", "btc_eth"),
]
OUT = ra.ROOT / "results/oos"


def hold(pairs):
    """Equal-weight buy and hold of the pairs, each bought when its data starts (1000 split evenly)."""
    start, end = pd.Timestamp("2018-01-01", tz="UTC"), pd.Timestamp("2021-11-08", tz="UTC")
    vals = []
    for p in pairs:
        df = pd.read_feather(ra.ROOT / f"user_data/data/binance/{p.replace('/', '_')}-1d.feather")
        df = df[(df.date >= start) & (df.date < end)]
        vals.append(df.close.iloc[-1] / df.close.iloc[0] * (1 - 0.001) ** 2)
    final = 1000 * sum(vals) / len(vals)
    years = (end - start).days / 365.25
    return {"final": round(final, 1), "cagr_pct": round(((final / 1000) ** (1 / years) - 1) * 100, 1)}


def main():
    res = {}
    for strat, group in RUNS:
        name = f"{strat}__{group}"
        run_dir = OUT / name
        if not (run_dir / "summary.json").exists():
            err = ra.backtest(strat, "spot", ra.GROUPS[group], TIMERANGE, run_dir, 4 * 3600)
            if err:
                print("ERROR", name, err)
                continue
            s = ra.summarize(run_dir, strat, "spot", group, TIMERANGE)
            s = {k: v for k, v in s.items() if not k.startswith("_")}
            (run_dir / "summary.json").write_text(json.dumps(s, indent=2))
        s = json.loads((run_dir / "summary.json").read_text())
        s["hold"] = hold(ra.GROUPS[group])
        res[name] = s
        print(name, s["cagr_pct"], "%/m, kritimas", s["max_drawdown_pct"], "metai", s["yearly_pct"],
              "| laikyti:", s["hold"])
    (ra.ROOT.parent / "results/oos_freqtrade.json").write_text(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
