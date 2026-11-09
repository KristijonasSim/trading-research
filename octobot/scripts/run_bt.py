#!/usr/bin/env python3
"""
Run one OctoBot built-in profile through OctoBot's own backtester on one pair group,
with the same rules as the freqtrade research: Binance spot, 2021-11-08 -> 2026-11-08,
1000 USDT start, 0.1% fee. Saves results/raw/<profile>__<group>/{summary.json,trades.json}.

Usage: PYTHONPATH=. .venv/bin/python scripts/run_bt.py <profile> <group>
"""
import asyncio, copy, json, os, shutil, sqlite3, sys, time, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

GROUPS = {
    "btc_eth": ["BTC/USDT", "ETH/USDT"],
    "alts10": ["XRP/USDT", "BNB/USDT", "SOL/USDT", "DOGE/USDT", "ADA/USDT",
               "TRX/USDT", "LINK/USDT", "AVAX/USDT", "LTC/USDT", "DOT/USDT"],
    # traditional markets (Dukascopy 1h data converted to OctoBot format)
    "us30": ["US30/USDT"], "nas100": ["NAS100/USDT"], "spx500": ["SPX500/USDT"], "xau": ["XAU/USDT"],
}
START_TS, END_TS = 1636329600, 1794096000  # 2021-11-08 / 2026-11-08 UTC
START_BALANCE = 1000.0
FEE_PCT = 0.1
RAW = ROOT / "results/raw"
TA_EVALS = ["ADXMomentumEvaluator", "BBMomentumEvaluator", "DeathAndGoldenCrossEvaluator",
            "DoubleMovingAverageTrendEvaluator", "EMADivergenceTrendEvaluator", "EMAMomentumEvaluator",
            "KlingerOscillatorMomentumEvaluator", "KlingerOscillatorReversalConfirmationMomentumEvaluator",
            "MACDMomentumEvaluator", "RSIMomentumEvaluator", "RSIWeightMomentumEvaluator",
            "StochasticRSIVolatilityEvaluator", "SuperTrendEvaluator", "InstantMAEvaluator"]
WORK = ROOT / "work"


def first_closes(group):
    con = sqlite3.connect(ROOT / f"backtesting/data/{group}.data")
    out = {}
    for p in GROUPS[group]:
        row = con.execute("select candle from ohlcv where symbol=? and time_frame='1d' "
                          "order by timestamp limit 1", (p,)).fetchone()
        out[p] = json.loads(row[0])[4]
    return out


def daily_closes(group):
    con = sqlite3.connect(ROOT / f"backtesting/data/{group}.data")
    out = {}
    for sym, c in con.execute("select symbol, candle from ohlcv where time_frame='1d'"):
        c = json.loads(c)
        out.setdefault(sym, {})[int(c[0])] = c[4]
    return out


def btc_start():
    con = sqlite3.connect(ROOT / "backtesting/data/btc_eth.data")
    row = con.execute("select candle from ohlcv where symbol='BTC/USDT' and time_frame='1d' "
                      "order by timestamp limit 1").fetchone()
    return json.loads(row[0])[4]


def prepare_profile(profile, group):
    """Copy the built-in profile and set the common research settings.
    Only pairs, starting money and fee are changed. Grid / staggered price levels are
    written for BTC in dollars, so they are scaled to each coin's price (same % distance)."""
    base_profile, _, only_eval = profile.partition("+")
    src = ROOT / "user/profiles" / base_profile
    dst_root = WORK / f"{profile}__{group}"
    shutil.rmtree(dst_root, ignore_errors=True)
    dst = dst_root / "profiles" / profile
    shutil.copytree(src, dst)
    pairs = GROUPS[group]
    if only_eval:
        # same built-in Daily Trading bot, but driven by one ready-made OctoBot indicator only
        tc = json.loads((dst / "tentacles_config.json").read_text())
        ev = tc["tentacle_activation"]["Evaluator"]
        for k in TA_EVALS:
            ev[k] = False
        ev[only_eval] = True
        (dst / "tentacles_config.json").write_text(json.dumps(tc, indent=2))
    pj = json.loads((dst / "profile.json").read_text())
    c = pj["config"]
    c["crypto-currencies"] = {p.split("/")[0]: {"enabled": True, "pairs": [p]} for p in pairs}
    c["exchanges"] = {"binance": {"enabled": True, "exchange-type": "spot"}}
    c["trading"]["reference-market"] = "USDT"
    c["trader-simulator"] = {"enabled": True, "fees": {"maker": FEE_PCT, "taker": FEE_PCT},
                             "starting-portfolio": {"USDT": START_BALANCE}}
    c.setdefault("trader", {})["enabled"] = False
    (dst / "profile.json").write_text(json.dumps(pj, indent=2))

    sc = dst / "specific_config"
    prices = first_closes(group)
    btc = btc_start()
    for fname in ("GridTradingMode.json", "StaggeredOrdersTradingMode.json"):
        f = sc / fname
        if not f.exists():
            continue
        cfg = json.loads(f.read_text())
        tmpl = next(s for s in cfg["pair_settings"] if s["pair"] == "BTC/USDT")
        new = []
        for p in pairs:
            s = copy.deepcopy(tmpl)
            s["pair"] = p
            k = prices[p] / btc
            if fname.startswith("Grid"):
                s["flat_spread"] = tmpl["flat_spread"] * k
                s["flat_increment"] = tmpl["flat_increment"] * k
            else:
                # default band 30k-60k (2x wide); centre it on the starting price
                s["lower_bound"] = prices[p] / 2 ** 0.5
                s["upper_bound"] = prices[p] * 2 ** 0.5
            new.append(s)
        cfg["pair_settings"] = new
        f.write_text(json.dumps(cfg, indent=2))

    cfg_file = dst_root / "config.json"
    base = json.loads((ROOT / "user/config.json").read_text())
    base["profile"] = pj["profile"]["id"]
    base["accepted_terms"] = True
    base["services"] = {}
    cfg_file.write_text(json.dumps(base, indent=2))
    return dst_root, dst, pj["profile"]["id"]


async def run(profile, group):
    import octobot_commons.configuration as cconf
    import octobot_commons.constants as cconst
    import octobot_tentacles_manager.api as tm_api
    import octobot.api as ob_api
    import octobot_trading.api as tapi
    import octobot.logger  # noqa

    tm_api.load_tentacles(verbose=False)
    work, prof_dir, pid = prepare_profile(profile, group)
    conf = cconf.Configuration(str(work / "config.json"), str(work / "profiles"))
    conf.read(should_raise=False, fill_missing_fields=True)
    conf.select_profile(pid)
    config = conf.config
    config[cconst.CONFIG_EXCHANGE_TYPE] = "spot"
    tsc = tm_api.get_tentacles_setup_config(str(prof_dir / "tentacles_config.json"))

    data_file = str(ROOT / f"backtesting/data/{group}.data")
    bt = ob_api.create_independent_backtesting(
        config, tsc, [data_file], "", enable_logs=False, stop_when_finished=False,
        enforce_total_databases_max_size_after_run=False, enable_storage=False,
        start_timestamp=START_TS, end_timestamp=END_TS,
        join_backtesting_timeout=60 * 60 * 6)
    t0 = time.time()
    await ob_api.initialize_and_run_independent_backtesting(bt)
    await ob_api.join_independent_backtesting(bt, timeout=60 * 60 * 6)
    ids = ob_api.get_independent_backtesting_exchange_manager_ids(bt)
    em = tapi.get_exchange_managers_from_exchange_ids(ids)[0]
    trades = []
    for t in tapi.get_trade_history(em):
        trades.append({
            "time": float(t.executed_time), "symbol": t.symbol, "side": t.side.value,
            "price": float(t.executed_price), "qty": float(t.executed_quantity),
            "fee_cost": float(t.fee.get("cost", 0) or 0) if t.fee else 0.0,
            "fee_ccy": (t.fee or {}).get("currency"),
        })
    import octobot_commons.enums as cenums
    hist = tapi.get_portfolio_historical_values(em, "USDT", cenums.TimeFrames.ONE_DAY)
    hist = [(float(h["time"]), float(h["value"])) for h in hist]
    portfolio = {k: float(v.total) for k, v in tapi.get_portfolio(em).items() if float(v.total)}
    await ob_api.stop_independent_backtesting(bt)
    return trades, portfolio, hist, time.time() - t0


def summarize(profile, group, trades, portfolio, hist, secs):
    """Equity = OctoBot's own daily portfolio value in USDT (marked to market)."""
    import datetime as dt
    equity = sorted((t, v) for t, v in hist if START_TS <= t < END_TS)
    yearly, prev, by_year = {}, START_BALANCE, {}
    for ts, v in equity:
        by_year[dt.datetime.fromtimestamp(ts, dt.timezone.utc).year] = v
    for y in sorted(by_year):
        yearly[str(y)] = round((by_year[y] / prev - 1) * 100, 1)
        prev = by_year[y]
    final = equity[-1][1]
    years = (END_TS - START_TS) / 86400 / 365.25
    peak, mdd = 0, 0
    for _, v in equity:
        peak = max(peak, v)
        mdd = max(mdd, 1 - v / peak if peak else 0)
    return {
        "strategy": profile, "group": group, "engine": "octobot 2.1.1",
        "trades": len(trades), "trades_per_year": round(len(trades) / years, 1),
        "final_usdt": round(final, 1),
        "total_return_pct": round((final / START_BALANCE - 1) * 100, 1),
        "cagr_pct": round(((final / START_BALANCE) ** (1 / years) - 1) * 100, 1) if final > 0 else -100.0,
        "yearly_pct": yearly,
        "max_drawdown_pct": round(mdd * 100, 1),
        "equity_days": len(equity),
        "end_holdings": {k: round(v, 6) for k, v in portfolio.items()},
        "runtime_min": round(secs / 60, 1),
    }


def main():
    profile, group = sys.argv[1], sys.argv[2]
    out = RAW / f"{profile}__{group}"
    out.mkdir(parents=True, exist_ok=True)
    try:
        trades, portfolio, hist, secs = asyncio.run(run(profile, group))
        (out / "trades.json").write_text(json.dumps(trades))
        s = summarize(profile, group, trades, portfolio, hist, secs)
        (out / 'equity.json').write_text(json.dumps(hist))
        (out / "summary.json").write_text(json.dumps(s, indent=2))
        (out / "error.txt").unlink(missing_ok=True)
        print(json.dumps(s))
    except Exception:
        (out / "error.txt").write_text(traceback.format_exc())
        print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
