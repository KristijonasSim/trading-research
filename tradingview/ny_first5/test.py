"""NY open first 5m candle strategy on NAS100 (user idea, 2026-11-11).
- Candle 1 = 09:30-09:35 New York. Bullish -> buy at its close, bearish -> sell.
- SL = the candle's open (risk = body). If body is "very small" (< K x median body of the
  previous 20 days' first candles), wait for candle 2 (09:35-09:40) and use it the same way;
  if that is small too -> no trade that day.
- TP: either a price target of 1R / 2R (body x 1 or 2), or a time exit after 1 / 2 candles.
  Anything still open at 16:00 is closed. Same-minute SL and TP -> SL (conservative).
- Cost: COST points per round trip (spread). 1m data used to see what is hit first.
"""
import glob, sys
import numpy as np, pandas as pd

COST = 1.5  # NAS100 points per trade
df = pd.concat(pd.read_csv(f, usecols=[0, 1, 2, 3, 4]) for f in sorted(glob.glob("data/NAS100_1m_*.csv")))
df["t"] = pd.to_datetime(df.timestamp, utc=True).dt.tz_convert("America/New_York")
df = df.drop_duplicates("t").set_index("t").sort_index()
df = df[(df.index >= "2023-11-10") & (df.index < "2026-11-10")]
days = {d: g.between_time("09:30", "15:59") for d, g in df.groupby(df.index.date)}
days = {d: g for d, g in days.items() if len(g) > 300 and g.index[0].strftime("%H:%M") == "09:30"}


def candle(g, k):  # k-th 5m candle of the session (0-based)
    c = g.iloc[5 * k: 5 * k + 5]
    return c.open.iloc[0], c.high.max(), c.low.min(), c.close.iloc[-1]


def run(K=0.25, tp="R1", hist=20):
    bodies, rows = [], []
    for d, g in days.items():
        o1, h1, l1, c1 = candle(g, 0)
        body1 = abs(c1 - o1)
        med = np.median(bodies[-hist:]) if len(bodies) >= 5 else None
        bodies.append(body1)
        if med is None:
            continue
        pick = None
        for k in (0, 1):
            o, h, l, c = candle(g, k)
            if abs(c - o) >= K * med:
                pick = (k, o, c); break
        if pick is None:
            rows.append((d, 0, 0.0, 0.0)); continue
        k, o, c = pick
        side = 1 if c > o else -1
        risk = abs(c - o)
        entry, sl = c, o
        rest = g.iloc[5 * (k + 1):]
        if tp.startswith("R"):
            target = entry + side * risk * float(tp[1:])
            exit_px = rest.close.iloc[-1]
            for _, b in rest.iterrows():
                hit_sl = b.low <= sl if side == 1 else b.high >= sl
                hit_tp = b.high >= target if side == 1 else b.low <= target
                if hit_sl: exit_px = sl; break
                if hit_tp: exit_px = target; break
        else:  # time exit after N candles, SL still active
            n = int(tp[1:]); w = rest.iloc[: 5 * n]
            exit_px = w.close.iloc[-1]
            for _, b in w.iterrows():
                if (b.low <= sl if side == 1 else b.high >= sl): exit_px = sl; break
        pnl = side * (exit_px - entry) - COST
        rows.append((d, side, pnl, pnl / risk))
    return pd.DataFrame(rows, columns=["date", "side", "pts", "R"])


def stats(t, name):
    tr = t[t.side != 0]
    r = tr.R.values
    eq = np.cumprod(1 + 0.01 * r)  # 1 % of balance risked per trade
    dd = (1 - eq / np.maximum.accumulate(eq)).max() * 100
    yrs = 3.0
    by = tr.groupby(pd.to_datetime(tr.date).dt.year).R.sum().round(1).to_dict()
    return dict(variant=name, trades=len(tr), skipped_days=int((t.side == 0).sum()),
                win_pct=round((r > 0).mean() * 100, 1), avg_R=round(r.mean(), 3), total_R=round(r.sum(), 1),
                points=round(tr.pts.sum()), cagr_1pct_risk=round((eq[-1] ** (1 / yrs) - 1) * 100, 1),
                max_dd_pct=round(dd, 1), R_by_year=by)


if __name__ == "__main__":
    out = []
    for K in (0.1, 0.25, 0.5):
        for tp in ("R1", "R2", "T1", "T2"):
            out.append(stats(run(K, tp), f"K={K} TP={tp}"))
    res = pd.DataFrame(out)
    pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 80)
    print(res.to_string(index=False))
    res.to_csv("results.csv", index=False)
    g0, g1 = list(days.values())[0], list(days.values())[-1]
    print("NAS100 buy&hold:", round(g0.open.iloc[0]), "->", round(g1.close.iloc[-1]),
          f"{((g1.close.iloc[-1] / g0.open.iloc[0]) ** (1 / 3) - 1) * 100:.1f} %/y", "days:", len(days))
