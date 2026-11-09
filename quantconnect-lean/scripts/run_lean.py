#!/usr/bin/env python3
"""
Run one QuantConnect Strategy Library algorithm in the Lean engine (Docker) with the research rules:
2021-11-08 -> 2026-11-08, 0.1% fee per trade, results scaled to a 1000 start.
The algorithm code is used as published; only dates, cash, fee and the data resolution
(daily or hourly) of the subscriptions are changed.

Usage: .venv/bin/python scripts/run_lean.py "<strategy folder>" <variant> <daily|hour>
"""
import json, re, shutil, subprocess, sys, datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "sources/strategies"
WORK = ROOT / "work"
RAW = ROOT / "results/raw"
START, END = dt.datetime(2021, 11, 8), dt.datetime(2026, 11, 8)
CASH = 100000  # Lean buys whole shares; a bigger account avoids rounding. Results are scaled to 1000.

WRAPPER = '''from AlgorithmImports import *
import strategy_main as _s
import inspect as _inspect

_Base = [c for n, c in _inspect.getmembers(_s, _inspect.isclass)
         if issubclass(c, QCAlgorithm) and c is not QCAlgorithm and c.__module__ == "strategy_main"][0]


class PctFee(FeeModel):
    """0.1%% of traded value, same as the crypto research."""
    def GetOrderFee(self, parameters):
        sec = parameters.Security
        value = abs(parameters.Order.AbsoluteQuantity * sec.Price) * sec.QuoteCurrency.ConversionRate
        return OrderFee(CashAmount(0.001 * value, "USD"))


class ResearchWrapper(_Base):
    def Initialize(self):
        _Base.Initialize(self)
        self.SetStartDate(2021, 11, 8)
        self.SetEndDate(2026, 11, 8)
        self.SetCash(%d)
        for sec in self.Securities.Values:
            sec.SetFeeModel(PctFee())

    def OnSecuritiesChanged(self, changes):
        for sec in changes.AddedSecurities:
            sec.SetFeeModel(PctFee())
        parent = getattr(_Base, "OnSecuritiesChanged", None)
        if parent is not None and parent is not QCAlgorithm.OnSecuritiesChanged:
            parent(self, changes)
''' % CASH


COMPAT = [  # old Lean API -> current Lean, logic unchanged
    (r"decimal\.Decimal\(", "float("), (r"\bDecimal\(", "float("),
    (r"self\.benchmark\b", "self.qc_benchmark"), (r"self\.universe\b", "self.qc_universe"),
]


def patch(code, res):
    target = {"daily": "Daily", "hour": "Hour"}[res]
    for a, b in COMPAT:
        code = re.sub(a, b, code)
    # research window and account size are set where the author set them (before any History calls)
    arg = r"\((?:[^()]|\([^()]*\))*\)"
    code = re.sub(r"self\.SetStartDate" + arg, "self.SetStartDate(2021, 11, 8)", code)
    code = re.sub(r"self\.SetEndDate" + arg, "self.SetEndDate(2026, 11, 8)", code)
    code = re.sub(r"self\.SetCash" + arg, f"self.SetCash({CASH})", code)
    code = code.expandtabs(4)
    # intraday data we do not have: any minute/second/tick subscription runs on the chosen resolution
    code = re.sub(r"Resolution\.(Minute|Second|Tick)\b", f"Resolution.{target}", code)
    out = []
    for line in code.splitlines():
        if re.search(r"Add(Equity|Forex|Security)\(|UniverseSettings\.Resolution", line):
            line = re.sub(r"Resolution\.(Daily|Minute|Hour|Second|Tick)", f"Resolution.{target}", line)
            # AddEquity("X") without resolution defaults to minute data
            line = re.sub(r"Add(Equity|Forex)\(([^,()]+)\)", rf"Add\1(\2, Resolution.{target})", line)
        out.append(line)
    return "\n".join(out) + "\n"


def equity_stats(result_json):
    d = json.loads(result_json.read_text())
    vals = d["charts"]["Strategy Equity"]["series"]["Equity"]["values"]
    pts = sorted((v[0], v[4] if isinstance(v, list) and len(v) > 4 else v[1]) for v in vals)
    by_day = {}
    for t, v in pts:
        by_day[dt.datetime.utcfromtimestamp(t).date()] = v
    days = sorted(by_day)
    eq = [(day, by_day[day] / CASH * 1000) for day in days]
    yearly, prev, by_year = {}, 1000.0, {}
    for day, v in eq:
        by_year[day.year] = v
    for y in sorted(by_year):
        yearly[str(y)] = round((by_year[y] / prev - 1) * 100, 1)
        prev = by_year[y]
    final = eq[-1][1]
    years = (END - START).days / 365.25
    peak, mdd = 0, 0
    for _, v in eq:
        peak = max(peak, v)
        mdd = max(mdd, 1 - v / peak)
    st = d.get("statistics", {})
    return {
        "final_usdt": round(final, 1),
        "total_return_pct": round((final / 1000 - 1) * 100, 1),
        "cagr_pct": round(((final / 1000) ** (1 / years) - 1) * 100, 1) if final > 0 else -100.0,
        "yearly_pct": yearly,
        "max_drawdown_pct": round(mdd * 100, 1),
        "trades": int(st.get("Total Orders", st.get("Total Trades", "0")) or 0),
        "fees": st.get("Total Fees"),
        "first_day": str(days[0]), "last_day": str(days[-1]),
    }


def main():
    folder, variant, res = sys.argv[1], sys.argv[2], sys.argv[3]
    name = f"{folder.split(' ')[0]}_{variant}_{res}"
    src = SRC / folder / variant
    algo = WORK / name / "algo"
    results = WORK / name / "results"
    shutil.rmtree(WORK / name, ignore_errors=True)
    algo.mkdir(parents=True)
    results.mkdir(parents=True)
    renames = {"oumle.py": "ou_mle.py"}  # file names lose "_" in the published page ids
    for f in src.glob("*.py"):
        # the QuantConnect cloud adds this import to every file automatically
        code = "from AlgorithmImports import *\n" + patch(f.read_text(), res)
        if folder.startswith("19 "):
            # delisted banks have no data and crash the scheduled event: drop them from the list
            for t in set(re.findall(r"'([A-Z]{1,5})'", code)):
                if not (ROOT / f"data/equity/usa/daily/{t.lower()}.zip").exists():
                    code = re.sub(rf"'{t}',?\s*", "", code)
        (algo / ("strategy_main.py" if f.name == "main.py" else renames.get(f.name, f.name))).write_text(code)
    (algo / "main.py").write_text(WRAPPER)
    cfg = {
        "environment": "backtesting", "algorithm-type-name": "ResearchWrapper",
        "algorithm-language": "Python", "algorithm-location": "/Algo/main.py",
        "data-folder": "/Data/", "results-destination-folder": "/Results",
        "close-automatically": True, "debugging": False,
        "log-handler": "QuantConnect.Logging.CompositeLogHandler",
        "messaging-handler": "QuantConnect.Messaging.Messaging",
        "job-queue-handler": "QuantConnect.Queues.JobQueue",
        "api-handler": "QuantConnect.Api.Api",
        "map-file-provider": "QuantConnect.Data.Auxiliary.LocalDiskMapFileProvider",
        "factor-file-provider": "QuantConnect.Data.Auxiliary.LocalDiskFactorFileProvider",
        "data-provider": "QuantConnect.Lean.Engine.DataFeeds.DefaultDataProvider",
        "object-store": "QuantConnect.Lean.Engine.Storage.LocalObjectStore",
        "data-aggregator": "QuantConnect.Lean.Engine.DataFeeds.AggregationManager",
        "show-missing-data-logs": False,
        "object-store-root": "/Results/storage",
    }
    (algo / "config.json").write_text(json.dumps(cfg, indent=2))
    import os
    cmd = ["docker", "run", "--rm", "--network", "none", "--user", f"{os.getuid()}:{os.getgid()}", "-e", "HOME=/tmp",
           "-v", f"{ROOT/'data'}:/Data:ro", "-v", f"{algo}:/Algo", "-v", f"{results}:/Results",
           "-w", "/Lean/Launcher/bin/Debug", "--entrypoint", "dotnet", "quantconnect/lean:latest",
           "QuantConnect.Lean.Launcher.dll", "--config", "/Algo/config.json"]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
    (WORK / name / "lean.log").write_text(p.stdout + "\n" + p.stderr)
    out = RAW / name
    out.mkdir(parents=True, exist_ok=True)
    rj = [f for f in results.glob("*.json") if not f.name.endswith(("-summary.json", "-order-events.json"))
          and "log" not in f.name]
    rj = [f for f in rj if '"Strategy Equity"' in f.read_text()]
    if not rj:
        err = "\n".join(l for l in (p.stdout + p.stderr).splitlines() if "ERROR" in l or "rror" in l)[-3000:]
        (out / "error.txt").write_text(err or "no result")
        print("ERROR", name, err[-800:])
        sys.exit(1)
    s = {"strategy": folder, "variant": variant, "resolution": res, **equity_stats(rj[0])}
    (out / "summary.json").write_text(json.dumps(s, indent=2))
    (out / "error.txt").unlink(missing_ok=True)
    print(json.dumps(s))


if __name__ == "__main__":
    main()
