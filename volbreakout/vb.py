#!/usr/bin/env python3
"""
Volatility Breakout (user's TradingView indicator) backtest + adaptation to 1h / 15m.

Rules (same as the Pine script):
  raw   = (close - EMA21) / ATR14 ;  score = z-score of raw over 60 bars
  entry = crossover(score, 1.2) and EMA9 > EMA21 > EMA55 and close > BB_upper(20, 2)
  exit  = close < trailing stop (trail = max(trail, close - 1.5*ATR14))
Execution: signal on bar close, filled at the NEXT bar open (no look-ahead). Long only.
Costs: COST_BPS per side (spread+slippage) + FIN_PA yearly financing while in a position (CFD).

Adaptation: every length is multiplied by a scale s (s=1: the daily numbers on intraday bars,
s=bars_per_day: the same time span as the daily version). Parameters (s, threshold, stop) are
chosen on TRAIN only, then reported on the unseen TEST period.

Usage: python vb.py            -> results/*.csv + results/summary.md
"""
import itertools, json, sys
from pathlib import Path
import numpy as np
import pandas as pd
from numba import njit

ROOT = Path(__file__).resolve().parent
DATA, RES = ROOT / "data", ROOT / "results"
TRAIN = ("2017-01-01", "2022-12-31")
TEST = ("2023-01-01", "2026-11-09")
COST_BPS = 2.0     # per side: index CFD spread ~1-2 pt on NAS100 (~0.01 %) + slippage
FIN_PA = 0.06      # long CFD overnight financing ~6 %/yr while in a position
SYMBOLS = ["NAS100", "US30", "SPX500", "GER40", "XAUUSD"]
TFS = {"1D": "1D", "4h": "4h", "1h": "1h", "15m": "15min"}
BASE = dict(lenF=9, lenM=21, lenS=55, bbLen=20, bbMult=2.0, atrLen=14, zLen=60, zThr=1.2, stopMul=1.5)


def load(sym, tf):
    df = pd.read_csv(DATA / f"{sym}_15m.csv", index_col=0, parse_dates=True)
    df.columns = [c.lower() for c in df.columns]
    df = df[df["volume"] > 0] if "volume" in df else df
    if tf != "15min":
        if tf == "1D":  # trading day = 22:00 UTC (17:00 New York) to 22:00 UTC
            df = df.copy()
            df.index = df.index + pd.Timedelta(hours=2)
        df = df.resample(tf).agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
        if tf == "1D":
            df = df[df.index.day_of_week < 5]
    return df[["open", "high", "low", "close"]]


def ema(x, n):
    return x.ewm(span=n, adjust=False).mean()


def indicators(df, p, s):
    L = lambda n: max(2, int(round(n * s)))
    c = df["close"]
    emaF, emaM, emaS = ema(c, L(p["lenF"])), ema(c, L(p["lenM"])), ema(c, L(p["lenS"]))
    bbm = c.rolling(L(p["bbLen"])).mean()
    bbu = bbm + p["bbMult"] * c.rolling(L(p["bbLen"])).std(ddof=0)
    tr = pd.concat([df["high"] - df["low"], (df["high"] - c.shift()).abs(), (df["low"] - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / L(p["atrLen"]), adjust=False).mean()
    raw = (c - emaM) / atr
    z = L(p["zLen"])
    score = (raw - raw.rolling(z).mean()) / raw.rolling(z).std(ddof=0)
    return dict(score=score.values, stack=((emaF > emaM) & (emaM > emaS)).values,
                band=(c > bbu).values, atr=atr.values)


@njit(cache=True)
def simulate(o, c, score, stack, band, atr, thr, stop, cost, fin_bar, start, end):
    n = len(c)
    eq = np.ones(n)
    inpos = False
    pending = 0  # +1 enter at next open, -1 exit at next open
    trail = 0.0
    entry_px = 0.0
    val = 1.0
    trades = 0
    bars_in = 0
    for i in range(start, end):
        # fills at this bar's open
        if pending == 1:
            entry_px = o[i]
            val *= (1 - cost)
            inpos = True
            trades += 1
        elif pending == -1:
            val *= o[i] / entry_px * (1 - cost)
            inpos = False
        pending = 0
        if inpos:
            bars_in += 1
            val *= (1 - fin_bar)
            eq[i] = val * c[i] / entry_px
            if c[i] < trail:
                pending = -1
            else:
                trail = max(trail, c[i] - stop * atr[i])
        else:
            eq[i] = val
            if i > 0 and score[i] > thr and score[i - 1] <= thr and stack[i] and band[i]:
                pending = 1
                trail = c[i] - stop * atr[i]
    if inpos:  # close at the end
        val *= c[end - 1] / entry_px * (1 - cost)
        eq[end - 1] = val
    return eq[start:end], trades, bars_in


def stats(eq, idx, trades, bars_in):
    years = (idx[-1] - idx[0]).days / 365.25
    final = eq[-1]
    mdd = float(np.max(1 - eq / np.maximum.accumulate(eq)))
    cagr = final ** (1 / years) - 1 if final > 0 else -1
    return dict(cagr=round(cagr * 100, 1), mdd=round(mdd * 100, 1), trades_y=round(trades / years, 1),
                in_mkt=round(bars_in / len(eq) * 100), final=round(final * 1000))


def hold(df, a, b):
    c = df["close"].loc[a:b]
    eq = (c / c.iloc[0]).values
    return stats(eq, c.index, 1, len(eq))


def run(df, p, s, a, b):
    ind = indicators(df, p, s)
    idx = df.index
    start, end = idx.searchsorted(pd.Timestamp(a, tz=idx.tz)), idx.searchsorted(pd.Timestamp(b, tz=idx.tz) + pd.Timedelta(days=1))
    bars_per_year = len(df) / ((idx[-1] - idx[0]).days / 365.25)
    eq, n, bi = simulate(df["open"].values, df["close"].values, np.nan_to_num(ind["score"], nan=-99),
                         ind["stack"], ind["band"], ind["atr"], p["zThr"], p["stopMul"],
                         COST_BPS / 1e4, FIN_PA / bars_per_year, start, end)
    return stats(eq, idx[start:end], n, bi)


def main():
    RES.mkdir(exist_ok=True)
    rows = []
    syms = sys.argv[1:] or SYMBOLS
    for sym in syms:
        if not (DATA / f"{sym}_15m.csv").exists():
            continue
        for tfn, tf in TFS.items():
            df = load(sym, tf)
            bpd = len(df) / df.index.normalize().nunique()  # bars per trading day
            hT, hS = hold(df, *TRAIN), hold(df, *TEST)
            # 1) original numbers as published
            base = {"sym": sym, "tf": tfn, "bars_day": round(bpd, 1), "hold_train": hT["cagr"], "hold_test": hS["cagr"],
                    "hold_test_mdd": hS["mdd"]}
            tr, te = run(df, BASE, 1, *TRAIN), run(df, BASE, 1, *TEST)
            rows.append({**base, "variant": "originalus", "s": 1, "zThr": 1.2, "stop": 1.5,
                         **{f"train_{k}": v for k, v in tr.items()}, **{f"test_{k}": v for k, v in te.items()}})
            # 2) grid on TRAIN, best by return / drawdown with at least 6 trades a year
            scales = [1, 2, 3] if tfn == "1D" else sorted({1, 2, 3, 4, 6, 8, 12, round(bpd / 2), round(bpd)})
            min_trades = 2 if tfn == "1D" else 6
            best, grid = None, []
            for s, thr, stop in itertools.product(scales, [0.8, 1.0, 1.2, 1.5, 2.0], [1.0, 1.5, 2.0, 3.0, 4.0, 6.0]):
                p = {**BASE, "zThr": thr, "stopMul": stop}
                r = run(df, p, s, *TRAIN)
                score = r["cagr"] / max(r["mdd"], 5) if r["trades_y"] >= min_trades else -99
                grid.append((score, s, thr, stop, r))
            grid.sort(key=lambda g: -g[0])
            for rank, (score, s, thr, stop, r) in enumerate(grid[:3], 1):
                te = run(df, {**BASE, "zThr": thr, "stopMul": stop}, s, *TEST)
                rows.append({**base, "variant": f"pritaikytas_top{rank}", "s": s, "zThr": thr, "stop": stop,
                             **{f"train_{k}": v for k, v in r.items()}, **{f"test_{k}": v for k, v in te.items()}})
            print(sym, tfn, "done", flush=True)
    out = pd.DataFrame(rows)
    out.to_csv(RES / "results.csv", index=False)
    cols = ["sym", "tf", "variant", "s", "zThr", "stop", "train_cagr", "train_mdd", "train_trades_y",
            "test_cagr", "test_mdd", "test_trades_y", "test_in_mkt", "hold_test", "hold_test_mdd"]
    (RES / "summary.md").write_text(out[cols].to_markdown(index=False))
    print(out[cols].to_string(index=False))


if __name__ == "__main__":
    main()
