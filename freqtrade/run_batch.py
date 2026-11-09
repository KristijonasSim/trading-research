#!/usr/bin/env python3
"""
Backtest the 50 strategies in user_data/strategies/batch50 (unknown authors) INSIDE Docker
without network (freqtradeorg/freqtrade:stable, --network none, user_data read-only),
same rules as run_all.py: 2021-11-08..2026-11-08, Binance spot, 0.1 % fee, 1000 USDT,
groups btc_eth and alts10. Resumable: finished runs (summary.json) are skipped.

Usage: [BATCH=batch50b] .venv/bin/python run_batch.py [-j 3]
Output: results/batch50/<group>__<strategy>/ and ../results/batch50_results.csv
"""
import argparse, json, os, subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pandas as pd
import run_all as ra

ROOT = ra.ROOT
import sys
# which strategy folder to run: env BATCH (default batch50); folder user_data/strategies/<BATCH>/ with _list.json
BATCH = os.environ.get("BATCH", "batch50")
OUT = ROOT / "results" / BATCH
LIST = json.loads((ROOT / "user_data/strategies" / BATCH / "_list.json").read_text())
IMAGE = "freqtrade-research:latest"  # docker_image/Dockerfile: stable + ta, finta, arrow


def run(strategy, group, cfg="config_spot.json"):
    name = f"{group}__{strategy}"
    d = OUT / name
    if (d / "summary.json").exists() or (d / "error.txt").exists():
        return name, "skip"
    d.mkdir(parents=True, exist_ok=True)
    cmd = ["docker", "run", "--rm", "--network", "none", "--memory", "6g",
           "--user", f"{os.getuid()}:{os.getgid()}",
           "-v", f"{ROOT/'user_data'}:/freqtrade/user_data:ro",
           "-v", f"{ROOT/cfg}:/freqtrade/config.json:ro",
           "-v", f"{ROOT/'docker_offline'}:/offline:ro", "-e", "PYTHONPATH=/offline",
           "-v", f"{d}:/out", IMAGE, "backtesting",
           "--userdir", "/freqtrade/user_data", "-c", "/freqtrade/config.json",
           "--strategy-path", f"/freqtrade/user_data/strategies/{BATCH}", "--strategy", strategy,
           "--timerange", ra.TIMERANGE, "--pairs", *ra.GROUPS[group],
           "--max-open-trades", str(len(ra.GROUPS[group])),
           "--export", "trades", "--backtest-directory", "/out", "--cache", "none"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=3 * 3600)
        (d / "backtest.log").write_text(p.stdout + p.stderr)
        rc = p.returncode
    except subprocess.TimeoutExpired:
        (d / "error.txt").write_text("timeout 3h")
        return name, "timeout"
    if "price_side = \"other\"" in p.stdout + p.stderr and cfg == "config_spot.json":
        # strategy uses market orders: same test with entry/exit price_side = other
        return run(strategy, group, "config_spot_market.json")
    if rc != 0:
        (d / "error.txt").write_text("\n".join((p.stdout + p.stderr).splitlines()[-20:]))
        return name, "error"
    try:
        s = ra.summarize(d, strategy, "spot", group)
    except Exception as e:  # no trades / unreadable result
        (d / "error.txt").write_text(f"summary failed: {e!r}")
        return name, "error"
    s = {k: v for k, v in s.items() if not k.startswith("_")}
    (d / "summary.json").write_text(json.dumps(s, indent=2))
    return name, f"{s['cagr_pct']} %/m"


def report():
    rows = []
    for f in OUT.glob("*/summary.json"):
        s = json.loads(f.read_text())
        y = s.pop("yearly_pct")
        s["avg_year_pct"] = round(sum(y.values()) / len(y), 1) if y else 0
        rows.append({**s, **{k: v for k, v in y.items()}})
    errs = [f.parent.name for f in OUT.glob("*/error.txt")]
    df = pd.DataFrame(rows).sort_values("cagr_pct", ascending=False)
    df.to_csv(ROOT.parent / f"results/{BATCH}_results.csv", index=False)
    return df, errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-j", type=int, default=3)
    a = ap.parse_args()
    jobs = [(s, g) for s, _, _ in LIST for g in ("alts10", "btc_eth")]
    with ThreadPoolExecutor(a.j) as ex:
        for name, st in ex.map(lambda j: run(*j), jobs):
            print(name, st, flush=True)
    df, errs = report()
    print("DONE", len(df), "ok,", len(errs), "errors", flush=True)


if __name__ == "__main__":
    main()
