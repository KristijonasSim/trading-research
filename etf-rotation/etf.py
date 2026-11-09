#!/usr/bin/env python3
"""
Published ETF allocation / rotation strategies, one engine, the same rules for all:
  - signals on the last trading day of the month (close), trades at the NEXT day's open
    (daily strategies: signal on close, trade next open)
  - 0.1 % fee on traded value, start 1000, dividends included (Yahoo adjusted prices)
  - "cash" = BIL (T-bills)
Rules follow the authors' papers / posts; simplifications are noted next to each strategy.

Usage: ../quantconnect-lean/.venv/bin/python etf.py   -> results/summary.md, results/results.json
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
FEE = 0.001
C = pd.read_csv(ROOT / "data/close.csv", index_col=0, parse_dates=True)
O = pd.read_csv(ROOT / "data/open.csv", index_col=0, parse_dates=True)
U = pd.read_csv(ROOT / "data/unrate.csv", parse_dates=["observation_date"]).set_index("observation_date")["UNRATE"]
U.index = U.index + pd.offsets.MonthEnd(1) + pd.offsets.MonthEnd(1)  # month M is published in M+1: usable at end of M+1
ME = C.groupby(C.index.to_period("M")).tail(1).index  # month-end trading days
CM = C.loc[ME]  # month-end closes


def ret(asof, t, months):
    m = CM.loc[:asof, t]
    return m.iloc[-1] / m.iloc[-1 - months] - 1


def m13612w(asof, t):
    return 12 * ret(asof, t, 1) + 4 * ret(asof, t, 3) + 2 * ret(asof, t, 6) + ret(asof, t, 12)


def m13612u(asof, t):
    return (ret(asof, t, 1) + ret(asof, t, 3) + ret(asof, t, 6) + ret(asof, t, 12)) / 4


def sma_mom(asof, t, n=12):  # price / 12-month SMA - 1 (Keller BAA "SMA12")
    m = CM.loc[:asof, t]
    return m.iloc[-1] / m.iloc[-n:].mean() - 1


def best(asof, ts, f, k=1):
    return sorted(ts, key=lambda t: -f(asof, t))[:k]


def eq(ts, w=1.0):
    return {t: w / len(ts) for t in ts}


def add(*ds):
    out = {}
    for d in ds:
        for k, v in d.items():
            out[k] = out.get(k, 0) + v
    return out


# ---------------- strategies: f(asof) -> target weights ----------------
G12 = ["SPY", "IWM", "QQQ", "VGK", "EWJ", "EEM", "VNQ", "DBC", "GLD", "TLT", "HYG", "LQD"]


def gem(a):  # Antonacci 2014
    if ret(a, "SPY", 12) > ret(a, "BIL", 12):
        return {best(a, ["SPY", "EFA"], lambda a, t: ret(a, t, 12))[0]: 1}
    return {"AGG": 1}


def adm(a):  # Accelerating Dual Momentum (EngineeredPortfolio 2018), ETF version
    s = {t: ret(a, t, 1) + ret(a, t, 3) + ret(a, t, 6) for t in ["SPY", "SCZ"]}
    top = max(s, key=s.get)
    return {top: 1} if s[top] > 0 else {"TLT": 1}


def composite_dm(a):  # Antonacci composite: 4 modules, 25 % each
    out = {}
    for x, y in [("SPY", "EFA"), ("HYG", "LQD"), ("VNQ", "REM"), ("GLD", "TLT")]:
        t = x if ret(a, x, 12) >= ret(a, y, 12) else y
        t = t if ret(a, t, 12) > ret(a, "BIL", 12) else "BIL"
        out = add(out, {t: .25})
    return out


def vaa_g4(a):  # Keller & Keuning 2017
    off, de = ["SPY", "EFA", "EEM", "AGG"], ["LQD", "IEF", "SHY"]
    if all(m13612w(a, t) > 0 for t in off):
        return {best(a, off, m13612w)[0]: 1}
    return {best(a, de, m13612w)[0]: 1}


def vaa_g12(a):  # top 2, breadth B=4
    de = ["LQD", "IEF", "SHY"]
    bad = sum(m13612w(a, t) <= 0 for t in G12)
    cf = min(1, bad / 4)
    return add(eq(best(a, G12, m13612w, 2), 1 - cf), {best(a, de, m13612w)[0]: cf})


def daa(a, risky=G12, top=6):  # Keller & Keuning 2018, canaries VWO + BND
    bad = sum(m13612w(a, t) <= 0 for t in ["VWO", "BND"])
    cf = bad / 2
    return add(eq(best(a, risky, m13612w, top), 1 - cf), {best(a, ["SHY", "IEF", "LQD"], m13612w)[0]: cf})


def daa_g4(a):
    return daa(a, ["SPY", "VEA", "VWO", "BND"], 1)


def baa(a, off=G12, top=6):  # Keller 2022 Bold Asset Allocation
    if any(m13612w(a, t) <= 0 for t in ["SPY", "VWO", "VEA", "BND"]):
        de = ["TIP", "DBC", "BIL", "IEF", "TLT", "LQD", "AGG"]
        pick = best(a, de, sma_mom, 3)
        pick = [t if sma_mom(a, t) >= sma_mom(a, "BIL") else "BIL" for t in pick]
        return add(*[{t: 1 / 3} for t in pick])
    return eq(best(a, off, sma_mom, top))


def baa_g4(a):
    return baa(a, ["QQQ", "EEM", "EFA", "AGG"], 1)


def paa(a):  # Keller 2016 Protective Asset Allocation, a=2, top 6
    n = sum(sma_mom(a, t) > 0 for t in G12)
    bf = min(1, (12 - n) / (12 - 6))
    good = [t for t in best(a, G12, sma_mom, 6) if sma_mom(a, t) > 0]
    return add(eq(good, 1 - bf) if good else {}, {"IEF": bf if good else 1})


def haa(a):  # Keller 2023 Hybrid Asset Allocation (balanced)
    if m13612u(a, "TIP") <= 0:
        return {best(a, ["BIL", "IEF"], m13612u)[0]: 1}
    off = ["SPY", "IWM", "VEA", "VWO", "VNQ", "DBC", "IEF", "TLT"]
    safe = best(a, ["BIL", "IEF"], m13612u)[0]
    return add(*[{t if m13612u(a, t) > 0 else safe: .25} for t in best(a, off, m13612u, 4)])


def gtaa(a, ts):  # Faber 2007: each asset only above its 10-month SMA
    return add(*[{t if sma_mom(a, t, 10) > 0 else "BIL": 1 / len(ts)} for t in ts])


def gtaa5(a):
    return gtaa(a, ["SPY", "EFA", "IEF", "VNQ", "DBC"])


def gtaa13(a):
    return gtaa(a, ["SPY", "IWM", "EFA", "EEM", "VNQ", "RWX", "IEF", "TLT", "TIP", "LQD", "BWX", "DBC", "GLD"])


def aaa(a):  # Adaptive Asset Allocation (Butler 2012); min-variance simplified to inverse volatility
    u = ["SPY", "EFA", "EEM", "VNQ", "RWX", "IEF", "TLT", "DBC", "GLD", "LQD"]
    top = best(a, u, lambda a, t: ret(a, t, 6), 5)
    d = C.loc[:a, top].iloc[-60:].pct_change().std()
    w = (1 / d) / (1 / d).sum()
    return w.to_dict()


def laa(a):  # Keuning 2019 Lethargic Asset Allocation
    spy = C.loc[:a, "SPY"]
    un = U.loc[:a]
    risk_off = spy.iloc[-1] < spy.iloc[-200:].mean() and un.iloc[-1] > un.iloc[-12:].mean()
    return {"IWD": .25, "GLD": .25, "IEF": .25, ("SHY" if risk_off else "QQQ"): .25}


def sector(a):  # 12-1 momentum, top 3 of 9 SPDR sectors
    xs = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
    f = lambda a, t: CM.loc[:a, t].iloc[-2] / CM.loc[:a, t].iloc[-13] - 1
    return eq(best(a, xs, f, 3))


def sell_in_may(a):
    return {"SPY": 1} if a.month in (10, 11, 12, 1, 2, 3) else {"BIL": 1}  # signal at month end -> held next month


STATIC = {
    "Permanent Portfolio": {"SPY": .25, "TLT": .25, "GLD": .25, "SHY": .25},
    "All Weather": {"SPY": .30, "TLT": .40, "IEF": .15, "GLD": .075, "DBC": .075},
    "Golden Butterfly": {"SPY": .2, "IWN": .2, "TLT": .2, "SHY": .2, "GLD": .2},
    "60/40 (palyginimui)": {"SPY": .6, "AGG": .4},
    "HFEA UPRO/TMF 55/45": {"UPRO": .55, "TMF": .45},
}

MONTHLY = {
    "GEM Dual Momentum": (gem, 2014), "Accelerating Dual Momentum": (adm, 2018),
    "Composite Dual Momentum": (composite_dm, 2015), "VAA-G4": (vaa_g4, 2017), "VAA-G12": (vaa_g12, 2017),
    "DAA-G12": (daa, 2018), "DAA-G4 (Canary)": (daa_g4, 2018), "BAA-G12": (baa, 2022), "BAA-G4": (baa_g4, 2022),
    "PAA": (paa, 2016), "HAA": (haa, 2023), "GTAA5 (Faber)": (gtaa5, 2007), "GTAA13 / Ivy": (gtaa13, 2009),
    "Adaptive Asset Allocation": (aaa, 2012), "Lethargic Asset Allocation": (laa, 2019),
    "Sector rotation 12-1": (sector, 2010), "Sell in May": (sell_in_may, 1990),
}
PUBLISHED = {"Permanent Portfolio": 1981, "All Weather": 2012, "Golden Butterfly": 2016,
             "60/40 (palyginimui)": 0, "HFEA UPRO/TMF 55/45": 2019,
             "SPY > 200 d. vidurkis": 2000, "TQQQ kai QQQ > 200 d.": 2019, "Laikyti SPY": 0}


def daily_signal(kind):
    def f(d):
        if kind == "spy200":
            s = C.loc[:d, "SPY"]
            return {"SPY": 1} if s.iloc[-1] > s.iloc[-200:].mean() else {"BIL": 1}
        s = C.loc[:d, "QQQ"]
        return {"TQQQ": 1} if s.iloc[-1] > s.iloc[-200:].mean() else {"BIL": 1}
    return f


def simulate(fn, start, end, rebal="M"):
    days = C.loc[start:end].index
    if rebal == "M":
        sig_days = set(ME)
    elif rebal == "Q":
        sig_days = set(d for d in ME if d.month in (3, 6, 9, 12))
    elif rebal == "Y":
        sig_days = set(d for d in ME if d.month == 12)
    else:
        sig_days = set(days)
    cash, qty, val, pending, trades = 1000.0, {}, [], None, 0
    first = True
    for i, d in enumerate(days):
        if first or pending is not None:
            w = pending if pending is not None else fn(C.index[C.index.get_loc(d) - 1])
            px = O.loc[d]
            e = cash + sum(q * px[t] for t, q in qty.items())
            new = {t: wt * e / px[t] for t, wt in w.items() if wt > 0}
            turnover = sum(abs(new.get(t, 0) - qty.get(t, 0)) * px[t] for t in set(new) | set(qty))
            if turnover > 0.001 * e:
                fee = turnover * FEE
                cash = e - fee - sum(q * px[t] for t, q in new.items())
                qty = new
                trades += 1
            pending, first = None, False
        if d in sig_days and i < len(days) - 1:
            pending = fn(d)
        val.append(cash + sum(q * C.loc[d, t] for t, q in qty.items()))
    return pd.Series(val, index=days)


def stats(s, published=None):
    yrs = (s.index[-1] - s.index[0]).days / 365.25
    out = {"cagr": round(((s.iloc[-1] / s.iloc[0]) ** (1 / yrs) - 1) * 100, 1),
           "mdd": round(float((1 - s / s.cummax()).max()) * 100, 1),
           "final": round(float(s.iloc[-1] / s.iloc[0] * 1000))}
    r = s.pct_change().dropna()
    out["sharpe"] = round(float(r.mean() / r.std() * np.sqrt(252)), 2)
    # 2008 crash: from 2008-07-01 to the market bottom 2009-03-09 (only if the strategy already ran)
    out["gfc"] = round((s.loc[:"2009-03-09"].iloc[-1] / s.loc["2008-07-01":].iloc[0] - 1) * 100, 1) if s.index[0] <= pd.Timestamp("2008-07-01") else None
    out["y2022"] = round((s.loc["2022"].iloc[-1] / s.loc["2021"].iloc[-1] - 1) * 100, 1)
    if published and published + 1 > s.index[0].year:
        p = s.loc[f"{published + 1}-01-01":]
        if len(p) > 252:
            y = (p.index[-1] - p.index[0]).days / 365.25
            out["after_pub_cagr"] = round(((p.iloc[-1] / p.iloc[0]) ** (1 / y) - 1) * 100, 1)
    return out


def main():
    res = {}
    END = "2026-11-06"
    for name, w in STATIC.items():
        start = "2011-01-03" if "HFEA" in name else "2008-07-01"
        res[name] = (simulate(lambda d, w=w: w, start, END, "Q" if "HFEA" in name else "Y"), PUBLISHED[name])
    for name, (fn, pub) in MONTHLY.items():
        start = "2009-01-02" if name in ("Accelerating Dual Momentum",) else "2008-07-01"
        if name in ("BAA-G12", "BAA-G4", "GTAA13 / Ivy"):
            start = "2008-11-03"
        res[name] = (simulate(fn, start, END), pub)
    res["SPY > 200 d. vidurkis"] = (simulate(daily_signal("spy200"), "2008-07-01", END, "D"), 2000)
    res["TQQQ kai QQQ > 200 d."] = (simulate(daily_signal("tqqq"), "2011-01-03", END, "D"), 2019)
    res["Laikyti SPY"] = (simulate(lambda d: {"SPY": 1}, "2008-07-01", END, "Y"), 0)
    res["Laikyti QQQ"] = (simulate(lambda d: {"QQQ": 1}, "2008-07-01", END, "Y"), 0)

    rows = []
    for name, (s, pub) in res.items():
        full = stats(s, pub)
        common = stats(s.loc["2011-01-03":] / s.loc["2011-01-03":].iloc[0] * 1000)
        rows.append({"strategija": name, "nuo": str(s.index[0].date()), "%/m": full["cagr"], "kritimas": full["mdd"],
                     "sharpe": full["sharpe"], "2008-07..2009-03": full["gfc"], "2022": full["y2022"],
                     "2011-26 %/m": common["cagr"], "2011-26 kritimas": common["mdd"],
                     "paskelbta": pub or "", "po paskelbimo %/m": full.get("after_pub_cagr")})
    df = pd.DataFrame(rows).sort_values("sharpe", ascending=False)
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results/summary.md").write_text(df.to_markdown(index=False))
    eqs = pd.DataFrame({n: s for n, (s, _) in res.items()})
    eqs.to_csv(ROOT / "results/equity.csv")
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
