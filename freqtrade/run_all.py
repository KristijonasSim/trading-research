#!/usr/bin/env python3
"""
Runs every strategy through the same Freqtrade backtest on two pair groups
(BTC+ETH, top-10 altcoins) and saves one summary row per run.

Usage:
  .venv/bin/python run_all.py                # all strategies, 3 parallel workers
  .venv/bin/python run_all.py -s Strategy001 # only one strategy
  .venv/bin/python run_all.py -j 4           # more workers
Already finished runs are skipped (delete results/raw/<run> to redo).
"""
import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FT = ROOT / ".venv/bin/freqtrade"
RAW = ROOT / "results/raw"
TIMERANGE = "20211108-20261108"
START_BALANCE = 1000.0

MAJORS = ["BTC/USDT", "ETH/USDT"]
ALTS = ["XRP/USDT", "BNB/USDT", "SOL/USDT", "DOGE/USDT", "ADA/USDT",
        "TRX/USDT", "LINK/USDT", "AVAX/USDT", "LTC/USDT", "DOT/USDT"]
SCREEN = ["SOL/USDT", "XRP/USDT", "ADA/USDT"]
GROUPS = {"btc_eth": MAJORS, "alts10": ALTS, "screen3": SCREEN}
DEFAULT_GROUPS = ["btc_eth", "alts10"]

SKIP = {"DoesNothingStrategy"}  # example that never trades


def list_strategies(mode):
    out = subprocess.run(
        [str(FT), "list-strategies", "--userdir", "user_data",
         "--strategy-path", f"user_data/strategies/{mode}", "-1"],
        cwd=ROOT, capture_output=True, text=True).stdout
    names = []
    for line in out.splitlines():
        line = line.strip()
        if line and " " not in line and not line.startswith(("{", "}", '"', "Add", "to")):
            names.append(line)
    return [n for n in names if n not in SKIP]


def classify(avg_minutes):
    if avg_minutes is None:
        return "-"
    if avg_minutes < 60:
        return "scalping"
    if avg_minutes < 24 * 60:
        return "day trading"
    if avg_minutes < 14 * 24 * 60:
        return "swing"
    return "position"


def summarize(run_dir, strategy, mode, group, timerange=TIMERANGE):
    from freqtrade.data.btanalysis import load_backtest_data, load_backtest_stats

    stats = load_backtest_stats(run_dir)
    s = stats["strategy"][strategy]
    trades = load_backtest_data(run_dir, strategy)

    start = datetime.strptime(timerange.split("-")[0], "%Y%m%d")
    end = datetime.strptime(timerange.split("-")[1], "%Y%m%d")
    years = (end - start).days / 365.25

    final = START_BALANCE + float(trades["profit_abs"].sum()) if len(trades) else START_BALANCE
    cagr = (final / START_BALANCE) ** (1 / years) - 1 if final > 0 else -1.0

    yearly = {}
    if len(trades):
        t = trades.sort_values("close_date")
        bal = START_BALANCE
        for y, grp in t.groupby(t["close_date"].dt.year):
            p = float(grp["profit_abs"].sum())
            yearly[str(y)] = round(p / bal * 100, 1) if bal > 0 else None
            bal += p
        avg_min = float((t["close_date"] - t["open_date"]).dt.total_seconds().mean() / 60)
    else:
        avg_min = None

    return {
        "strategy": strategy,
        "mode": mode,
        "group": group,
        "timeframe": s.get("timeframe"),
        "style": classify(avg_min),
        "avg_trade_hours": round(avg_min / 60, 1) if avg_min is not None else None,
        "trades": int(s["total_trades"]),
        "trades_per_year": round(s["total_trades"] / years, 1),
        "total_return_pct": round((final / START_BALANCE - 1) * 100, 1),
        "cagr_pct": round(cagr * 100, 1),
        "yearly_pct": yearly,
        "max_drawdown_pct": round(float(s.get("max_drawdown_account", 0)) * 100, 1),
        "win_rate_pct": round(float(s.get("winrate", 0)) * 100, 1),
        "profit_factor": round(float(s.get("profit_factor", 0) or 0), 2),
        "market_change_pct": round(float(s.get("market_change", 0)) * 100, 1),
        "timerange": timerange,
        "_avg_min": avg_min,
        "_wins": float(s.get("winrate", 0)) * int(s["total_trades"]),
    }


def year_segments():
    a, b = TIMERANGE.split("-")
    segs, cur = [], a
    for y in range(int(a[:4]) + 1, int(b[:4]) + 1):
        segs.append((str(y - 1), f"{cur}-{y}0101"))
        cur = f"{y}0101"
    segs.append((b[:4], f"{cur}-{b}"))
    return segs


def combine_years(parts, strategy, mode, group):
    """Merge per-year runs (each starts with a fresh 1000 USDT) into one summary.
    Total/CAGR compound the yearly returns; drawdown is the worst single year."""
    years = sum((datetime.strptime(tr.split("-")[1], "%Y%m%d")
                 - datetime.strptime(tr.split("-")[0], "%Y%m%d")).days
                for tr in (p["timerange"] for p in parts)) / 365.25
    growth, yearly = 1.0, {}
    for (y, _), p in zip(year_segments(), parts):
        r = p["total_return_pct"] / 100
        yearly[y] = round(r * 100, 1)
        growth *= 1 + r
    market = 1.0
    for p in parts:
        market *= 1 + p["market_change_pct"] / 100
    trades = sum(p["trades"] for p in parts)
    mins = [p["_avg_min"] * p["trades"] for p in parts if p["_avg_min"] is not None]
    avg_min = sum(mins) / trades if trades else None
    return {
        "strategy": strategy, "mode": mode, "group": group,
        "timeframe": parts[0]["timeframe"],
        "style": classify(avg_min),
        "avg_trade_hours": round(avg_min / 60, 1) if avg_min is not None else None,
        "trades": trades,
        "trades_per_year": round(trades / years, 1),
        "total_return_pct": round((growth - 1) * 100, 1),
        "cagr_pct": round((growth ** (1 / years) - 1) * 100, 1) if growth > 0 else -100.0,
        "yearly_pct": yearly,
        "max_drawdown_pct": max(p["max_drawdown_pct"] for p in parts),
        "win_rate_pct": round(sum(p["_wins"] for p in parts) / trades * 100, 1) if trades else 0,
        "profit_factor": None,
        "market_change_pct": round((market - 1) * 100, 1),
        "timerange": TIMERANGE,
        "note": "run year by year (memory); each year restarts at 1000 USDT",
    }


def backtest(strategy, mode, pairs, timerange, run_dir, timeout):
    """Returns None on success, else an error string."""
    run_dir.mkdir(parents=True, exist_ok=True)
    cmd = [str(FT), "backtesting", "--userdir", "user_data",
           "-c", "config_futures.json" if mode == "futures" else "config_spot.json",
           "--strategy-path", f"user_data/strategies/{mode}",
           "--strategy", strategy,
           "--timerange", timerange,
           "--pairs", *pairs,
           "--max-open-trades", str(len(pairs)),
           "--export", "trades",
           "--backtest-directory", str(run_dir),
           "--cache", "none"]
    log = run_dir / "backtest.log"
    try:
        with open(log, "w") as fh:
            rc = subprocess.run(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT,
                                timeout=timeout).returncode
    except subprocess.TimeoutExpired:
        return f"timeout after {timeout}s"
    if rc != 0:
        return "\n".join(log.read_text().splitlines()[-15:]) or f"rc={rc}"
    return None


def strategy_timeframe(strategy, mode):
    import re
    for f in (ROOT / "user_data/strategies" / mode).glob("*.py"):
        txt = f.read_text()
        m = re.search(rf"class {strategy}\b.*?^\s*timeframe\s*=\s*['\"](\w+)['\"]",
                      txt, re.S | re.M)
        if m:
            return m.group(1)
    return None


def run_one(strategy, mode, group, timeout, force_yearly=False):
    pairs = GROUPS[group]
    if mode == "futures":
        pairs = [p + ":USDT" for p in pairs]
    name = f"{mode}__{group}__{strategy}"
    run_dir = RAW / name
    summary_file = run_dir / "summary.json"
    if summary_file.exists():
        return name, "skip (done)"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "error.txt").unlink(missing_ok=True)

    # 1m data for 10 pairs x 5 years does not fit in RAM -> run year by year
    yearly = force_yearly or (len(pairs) > 2 and strategy_timeframe(strategy, mode) == "1m")
    try:
        if yearly:
            parts = []
            for y, tr in year_segments():
                sub = run_dir / f"y{y}"
                sf = sub / "summary.json"
                if not sf.exists():
                    err = backtest(strategy, mode, pairs, tr, sub, timeout)
                    if err:
                        (run_dir / "error.txt").write_text(f"[{y}] {err}")
                        return name, f"FAILED ({y})"
                    sf.write_text(json.dumps(summarize(sub, strategy, mode, group, tr)))
                parts.append(json.loads(sf.read_text()))
            summary = combine_years(parts, strategy, mode, group)
        else:
            err = backtest(strategy, mode, pairs, TIMERANGE, run_dir, timeout)
            if err:
                (run_dir / "error.txt").write_text(err)
                return name, "FAILED"
            summary = summarize(run_dir, strategy, mode, group)
    except Exception as e:  # noqa: BLE001
        (run_dir / "error.txt").write_text(f"summary error: {e!r}")
        return name, f"FAILED (summary: {e})"
    summary = {k: v for k, v in summary.items() if not k.startswith("_")}
    summary_file.write_text(json.dumps(summary, indent=2))
    return name, f"ok  {summary['cagr_pct']:>7}%/yr  trades={summary['trades']}" + \
        ("  [yearly]" if yearly else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-s", "--strategy", nargs="*")
    ap.add_argument("-m", "--mode", choices=["spot", "futures", "extra"], nargs="*",
                    default=["spot", "futures"])
    ap.add_argument("-g", "--group", choices=list(GROUPS), nargs="*", default=DEFAULT_GROUPS)
    ap.add_argument("-x", "--exclude", nargs="*", default=[])
    ap.add_argument("-j", "--jobs", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=3 * 3600)
    ap.add_argument("--yearly", action="store_true",
                    help="run every backtest year by year (saves memory)")
    args = ap.parse_args()

    jobs = []
    for mode in args.mode:
        for strat in list_strategies(mode):
            if args.strategy and strat not in args.strategy:
                continue
            if strat in args.exclude:
                continue
            for group in args.group:
                jobs.append((strat, mode, group))
    # heavy strategy last so it doesn't block the queue
    jobs.sort(key=lambda j: j[0].startswith("NostalgiaForInfinity"))
    print(f"{len(jobs)} backtests queued", flush=True)

    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        futs = {ex.submit(run_one, *j, args.timeout, args.yearly): j for j in jobs}
        for i, f in enumerate(as_completed(futs), 1):
            name, status = f.result()
            print(f"[{i}/{len(jobs)}] {name}: {status}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
