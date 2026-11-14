"""Passivbot backtestų suvestinė iš balance_and_equity.csv.gz: CAGR, max kritimas (equity), metai. python3 passivbot/summary.py"""
import glob, os, json, pandas as pd
D = os.path.dirname(os.path.abspath(__file__))
for d in sorted(glob.glob(f"{D}/backtests/*/*/")):
    e = pd.read_csv(d + "balance_and_equity.csv.gz")
    tcol = [c for c in e.columns if "time" in c.lower() or c in ("ts", "timestamp", "minute")]
    eqc = [c for c in e.columns if "equity" in c.lower() and "usd" in c.lower()] or [c for c in e.columns if "equity" in c.lower()]
    cfg = json.load(open(d + "config.json"))
    s, en = cfg["backtest"]["start_date"], cfg["backtest"]["end_date"]
    eq = e[eqc[0]].values
    idx = pd.date_range(s, en, periods=len(eq))
    q = pd.Series(eq, idx); yrs = (idx[-1] - idx[0]).days / 365.25
    cagr = (q.iloc[-1] / q.iloc[0]) ** (1 / yrs) - 1 if q.iloc[-1] > 0 else -1
    dd = (q / q.cummax() - 1).min()
    yr = q.resample("YE").last(); yr = pd.concat([pd.Series([q.iloc[0]], [idx[0]]), yr]).pct_change().dropna()
    name = os.path.basename(d.rstrip("/")).split("Z_", 1)[1].split("_setup")[0]
    print(f"{name:40s} {s}–{en}: CAGR {cagr*100:+6.1f}%  kritimas {dd*100:5.0f}%  galutinis {q.iloc[-1]/q.iloc[0]:.2f}x | " + " ".join(f"{k.year}:{v*100:+.0f}" for k, v in yr.items()))
    print("   stulpeliai:", list(e.columns)[:8]) if os.environ.get("DBG") else None
