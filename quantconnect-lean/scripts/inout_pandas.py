#!/usr/bin/env python3
"""
In & Out (QuantConnect forum 9632, backtest b34d9b7dda) re-implemented in pandas, daily data.
Same signal logic as best_strategies/in_and_out_tqqq_tmf_quantconnect.py:
  - every day: signals from the last 252 daily closes (up to yesterday) -> in/out decision;
    when 'out', the out-weights are applied the same day
  - last trading day of the week: when 'in', the in-weights are applied
  - trades only when a position goes 0 -> >0 or >0 -> 0 (Thomas's trade reduction)
Execution: at the day's open (the original trades 2 h after the open; we only have daily bars).
Fee: 0.1% of traded value. Start: 1000.

Variants
  bug        : the published code as written. Its weight dict keeps TQQQ:1 forever and adds SPY:1,
               so TQQQ is never sold and the account can be up to 2x levered (Lean margin rules:
               an order is rejected when gross exposure would exceed 2x equity).
  fix_tqqq   : intended version: in = TQQQ 100 %, out = TMF 50 % + TYD 50 %.
  fix_spy    : in = SPY 100 %, out = TMF 50 % + TYD 50 %.
  fix_qqq    : no leverage at all: in = QQQ 100 %, out = TLT 50 % + IEF 50 %.

Usage: .venv/bin/python scripts/inout_pandas.py
Output: results/inout/inout_results.json and printed table.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw/daily_long"
OUT = ROOT / "results/inout"
FEE = 0.001
LEVERAGE = 2.0
INI_WAIT = 15

SIGNALS = ["XLI", "DBB", "IGE", "SHY", "UUP"]
PAIRS_T = ["GLD", "SLV", "XLU", "FXF", "FXA"]
MRKT = "SPY"
PERIODS = {
    "nematytas_2015_2021": ("2015-01-01", "2021-11-07"),
    "originalus_2021_2026": ("2021-11-08", "2026-11-08"),
    "visas_2015_2026": ("2015-01-01", "2026-11-08"),
}

VARIANTS = {
    "bug": dict(order=["TQQQ", "TMF", "TYD"], init={"TQQQ": 1, "TMF": .5, "TYD": .5},
                out={"SPY": 0, "TMF": .5, "TYD": .5}, inn={"SPY": 1, "TMF": 0, "TYD": 0}),
    "fix_tqqq": dict(order=["TQQQ", "TMF", "TYD"], init={"TQQQ": 1, "TMF": 0, "TYD": 0},
                     out={"TQQQ": 0, "TMF": .5, "TYD": .5}, inn={"TQQQ": 1, "TMF": 0, "TYD": 0}),
    "fix_spy": dict(order=["SPY", "TMF", "TYD"], init={"SPY": 1, "TMF": 0, "TYD": 0},
                    out={"SPY": 0, "TMF": .5, "TYD": .5}, inn={"SPY": 1, "TMF": 0, "TYD": 0}),
    "fix_qqq": dict(order=["QQQ", "TLT", "IEF"], init={"QQQ": 1, "TLT": 0, "IEF": 0},
                    out={"QQQ": 0, "TLT": .5, "IEF": .5}, inn={"QQQ": 1, "TLT": 0, "IEF": 0}),
}


def load():
    o, c = {}, {}
    for f in RAW.glob("*.csv"):
        df = pd.read_csv(f, index_col=0, parse_dates=True)
        o[f.stem], c[f.stem] = df["Open"], df["Close"]
    return pd.DataFrame(o).dropna(), pd.DataFrame(c).dropna()


def signal_series(close):
    """For each day t: (extreme signal any?, adjusted wait-days inputs) from closes up to t-1."""
    cols = SIGNALS + [MRKT] + PAIRS_T
    res = {}
    wd = INI_WAIT
    for i in range(253, len(close)):
        hist = close[cols].iloc[i - 252:i]  # 252 bars ending yesterday
        shift = sum(hist.shift(k) for k in range(55, 66)) / 11
        r = hist / shift - 1
        r["UUP"] = -r["UUP"]
        r["G_S"] = -(r["GLD"] - r["SLV"])
        r["U_I"] = -(r["XLU"] - r["XLI"])
        r["C_A"] = -(r["FXF"] - r["FXA"])
        pctl = np.nanpercentile(r.values, 1, axis=0)
        extreme = pd.Series(r.iloc[-1].values < pctl, index=r.columns)
        any_ext = bool(extreme[SIGNALS + ["G_S", "U_I", "C_A"]].any())

        def flip(a, b):
            return INI_WAIT if (r[a].iloc[-1] > 0 and r[b].iloc[-1] < 0 and r[b].iloc[-2] > 0) else 1
        wd = int(max(0.5 * wd, INI_WAIT * max(1, flip("GLD", "SLV"), flip("XLU", "XLI"), flip("FXF", "FXA"))))
        res[close.index[i]] = (any_ext, min(60, wd))
    return res


def backtest(opn, close, sig, v, start, end):
    days = close.loc[start:end].index
    cash, qty = 1000.0, {}
    wt = dict(v["init"])
    be_in, dcount, outday = True, 0, 0
    eq, inmkt, trades = [], [], 0
    week = pd.Series(days, index=days).groupby(days.to_period("W")).transform("max")

    def equity(px):
        return cash + sum(q * px[s] for s, q in qty.items())

    def set_holdings(sym, w, px):
        nonlocal cash, trades
        e = equity(px)
        target = w * e / px[sym]
        cur = qty.get(sym, 0.0)
        delta = target - cur
        if delta > 0:
            gross = sum(abs(q) * px[s] for s, q in qty.items())
            if gross + delta * px[sym] * (1 + FEE) > LEVERAGE * e + 1e-9:
                return  # Lean rejects the order: insufficient buying power
        cash -= delta * px[sym] + abs(delta) * px[sym] * FEE
        qty[sym] = target
        trades += 1

    def apply(px):
        for sym in list(wt):
            w = wt[sym]
            q = qty.get(sym, 0.0)
            if (q > 0 and w == 0) or (q == 0 and w > 0):
                set_holdings(sym, w, px)

    for d in days:
        px = opn.loc[d]
        ext, wait = sig[d]
        if ext:
            be_in, outday = False, dcount
        if dcount >= outday + wait:
            be_in = True
        dcount += 1
        if not be_in:
            wt.update(v["out"])
        apply(px)
        if week[d] == d and be_in:
            wt.update(v["inn"])
            apply(px)
        cpx = close.loc[d]
        e = equity(cpx)
        gross = sum(abs(q) * cpx[s] for s, q in qty.items())
        if e > 0 and gross > LEVERAGE * e:  # Lean margin call: cut every position pro rata back to 2x
            k = LEVERAGE * e / gross
            for s_ in qty:
                sold = qty[s_] * (1 - k)
                cash += sold * cpx[s_] * (1 - FEE)
                qty[s_] -= sold
            e = equity(cpx)
        eq.append(e)
        inmkt.append(be_in)
        if e <= 0:
            break
    return pd.Series(eq, index=days[:len(eq)]), trades, float(np.mean(inmkt))


def stats(eq, trades=None, in_pct=None):
    years = (eq.index[-1] - eq.index[0]).days / 365.25
    final = float(eq.iloc[-1])
    mdd = float((1 - eq / eq.cummax()).max())
    yearly, prev = {}, 1000.0
    for y, g in eq.groupby(eq.index.year):
        yearly[str(y)] = round((g.iloc[-1] / prev - 1) * 100, 1)
        prev = g.iloc[-1]
    cagr = ((final / 1000) ** (1 / years) - 1) * 100 if final > 0 else -100.0
    s = {"final": round(final, 1), "cagr_pct": round(cagr, 1),
         "max_drawdown_pct": round(mdd * 100, 1), "yearly_pct": yearly}
    if trades is not None:
        s["trades"] = trades
        s["in_market_pct"] = round(in_pct * 100)
    return s


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    opn, close = load()
    sig = signal_series(close)
    out = {}
    for pname, (a, b) in PERIODS.items():
        out[pname] = {}
        for vname, v in VARIANTS.items():
            eq, n, inp = backtest(opn, close, sig, v, a, b)
            out[pname][vname] = stats(eq, n, inp)
        for t in ["SPY", "QQQ", "TQQQ"]:
            c = close[t].loc[a:b]
            out[pname][f"hold_{t}"] = stats(c / c.iloc[0] * 1000 * (1 - FEE))
    (OUT / "inout_results.json").write_text(json.dumps(out, indent=2))
    for pname, rows in out.items():
        print(f"\n## {pname}")
        print(f"{'variantas':12} {'galas':>9} {'%/m':>6} {'kritimas':>8} {'sandoriai':>9} {'viduje%':>7}  metai")
        for k, s in rows.items():
            print(f"{k:12} {s['final']:9.0f} {s['cagr_pct']:6.1f} {s['max_drawdown_pct']:8.1f} "
                  f"{s.get('trades', ''):>9} {s.get('in_market_pct', ''):>7}  "
                  + " ".join(f"{y}:{r}" for y, r in s["yearly_pct"].items()))


if __name__ == "__main__":
    main()
