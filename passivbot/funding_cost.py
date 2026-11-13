"""Passivbot backtestas neįskaičiuoja funding. Įvertis: kiekvienos monetos pozicija (psize po kiekvieno fill) × perp dienos kaina × dienos funding suma
(papers/data/funding), padalinta iš balanso -> dienos nuostolis; pakoreguota CAGR. python3 passivbot/funding_cost.py <run_dir>"""
import sys, os, json, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__)); P = f"{H}/../papers/data"
d = sys.argv[1]; f = pd.read_csv(f"{d}/fills.csv", parse_dates=["timestamp"])
cfg = json.load(open(f"{d}/config.json")); s, e = cfg["backtest"]["start_date"], cfg["backtest"]["end_date"]
days = pd.date_range(s, e, freq="D")
bal = f.set_index("timestamp").usd_total_balance.resample("D").last().reindex(days).ffill().bfill()
cost = pd.Series(0.0, days)
for coin, g in f.groupby("coin"):
    ps = g.set_index("timestamp").psize.resample("D").last().reindex(days).ffill().fillna(0)
    fr = pd.read_csv(f"{P}/funding/{coin}USDT.csv"); fr = pd.Series(fr.rate.values, pd.to_datetime(fr.t, unit="ms")).resample("D").sum().reindex(days).fillna(0)
    px = pd.read_csv(f"{P}/perp_1d/{coin}USDT.csv"); px = pd.Series(px.c.values, pd.to_datetime(px.t, unit="ms")).reindex(days).ffill()
    cost += (ps * px * fr).fillna(0)
drag = cost / bal
yrs = (days[-1] - days[0]).days / 365.25
eq = pd.read_csv(f"{d}/balance_and_equity.csv.gz").usd_total_equity.values
cagr = (eq[-1] / eq[0]) ** (1 / yrs) - 1
adj = (1 + cagr) * np.exp(-drag.sum() / yrs) - 1
print(f"funding vidutiniškai {drag.sum() / yrs * 100:.1f} % balanso per metus; CAGR {cagr*100:+.1f}% -> su funding ~{adj*100:+.1f}%")
