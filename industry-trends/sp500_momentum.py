"""S&P 500 akcijų momentum su istorine indekso sudėtimi (fja05680/sp500) ir Yahoo kainomis.
Kas mėnesį (paskutinė prekybos diena) iš tuo metu indekse esančių akcijų atrenkama top N, sandoris kitos dienos uždarymu.
A) 12-1 momentum (grąža nuo −252 iki −21 d.), lygūs svoriai.
B) Clenow „Stocks on the Move“: 90 d. log-regresijos nuolydis (metinis) × R², tik virš 100 d. vidurkio, be > 15 % šuolių,
   svoriai pagal 1/ATR(20); naujų nepirkti, kai SPY < 200 d. vidurkio.
Mokestis 0,1 % nuo apyvartos. Ribotumas: ~40 % iš indekso išėjusių akcijų Yahoo neturi (išgyvenusiųjų iškraipymas).
"""
import sys
import numpy as np
import pandas as pd

d = sys.argv[1]
C = pd.read_pickle(f"{d}/closes.pkl")
C.columns = [c.replace("-", ".") for c in C.columns]
H = pd.read_csv(f"{d}/hist.csv", parse_dates=["date"]).set_index("date").tickers.str.split(",")
spy = C.pop("SPY")
R = C.pct_change(fill_method=None)
days = C.index[(C.index >= "2000-06-01")]
FREQ = sys.argv[2] if len(sys.argv) > 2 else "M"
me = pd.Series(days, days).groupby(days.to_period(FREQ)).last().values


def members(dt):
    return set(H[H.index <= dt].iloc[-1])


cov = {}
for dt in me[::12]:
    m = members(dt); cov[str(dt)[:4]] = round(100 * len([t for t in m if t in C.columns and not np.isnan(C.at[dt, t])]) / len(m))
print("indekso dalis su kainomis (%):", cov)

logc = np.log(C)
mom = C.shift(21) / C.shift(252) - 1
sma100 = C.rolling(100).mean()
gap = R.abs().rolling(90).max()
atr = (C.diff().abs()).rolling(20).mean()  # tik uždarymo kainos -> vid. |ΔP|
spy200 = spy.rolling(200).mean()


def clenow_score(dt):
    i = C.index.get_loc(dt)
    y = logc.iloc[i - 89:i + 1]
    x = np.arange(90)
    xm = x - x.mean()
    ym = y - y.mean()
    slope = (xm[:, None] * ym.values).sum(0) / (xm ** 2).sum()
    r2 = ((xm[:, None] * ym.values).sum(0) ** 2) / ((xm ** 2).sum() * (ym.values ** 2).sum(0))
    return pd.Series((np.exp(slope * 252) - 1) * r2, y.columns)


def backtest(kind, N, fee=0.001, regime=False):
    W = pd.DataFrame(0.0, C.index, C.columns)
    cur = pd.Series(dtype=float)
    for k, dt in enumerate(me[:-1]):
        m = [t for t in members(dt) if t in C.columns and not np.isnan(C.at[dt, t])]
        if kind == "mom":
            s = mom.loc[dt, m].dropna().sort_values(ascending=False)
            pick = s.index[:N]
            w = pd.Series(1.0 / N, pick)
        else:
            sc = clenow_score(dt)[m].dropna()
            ok = (C.loc[dt, sc.index] > sma100.loc[dt, sc.index]) & (gap.loc[dt, sc.index] < 0.15)
            sc = sc[ok].sort_values(ascending=False)
            pick = sc.index[:N]
            inv = 1 / (atr.loc[dt, pick] / C.loc[dt, pick])
            w = inv / inv.sum()
        if regime and spy.at[dt] < spy200.at[dt]:
            if kind == "mom":
                w = pd.Series(dtype=float)  # 12-1 su filtru: viskas į grynuosius
            else:
                w = w[w.index.isin(cur.index)]  # Clenow: naujų nepirkti, laikyti tik jau turimas
        cur = w
        nxt = C.index[C.index.get_loc(dt) + 1]
        end = me[k + 1]
        W.loc[nxt:end, :] = 0.0
        if len(w):
            W.loc[nxt:end, w.index] = w.values
    Wp = W.shift(1).fillna(0)
    ret = (Wp * R.fillna(0)).sum(axis=1) - W.diff().abs().sum(axis=1).fillna(0) * fee
    return ret[days]


def st(r, a, b):
    r = r[a:b]; eq = (1 + r).cumprod(); y = len(r) / 252
    return f"{100*(eq.iloc[-1]**(1/y)-1):5.1f}%/m krit.{100*(1-eq/eq.cummax()).max():3.0f}%"


P = [("2001-01-01", "2014-12-31"), ("2015-01-01", "2026-11-10"), ("2021-01-01", "2026-11-10")]
spyr = spy.pct_change()[days]
print(" " * 30 + " | ".join(f"{a[:4]}-{b[:4]}".ljust(19) for a, b in P))
print(f"{'laikyti SPY':30}" + " | ".join(st(spyr, a, b).ljust(19) for a, b in P))
res = {}
RUNS = [("12-1 top 10", ("mom", 10)), ("12-1 top 20", ("mom", 20)), ("12-1 top 50", ("mom", 50)),
        ("12-1 top 20 + SPY filtras", ("mom", 20, 0.001, True)),
        ("Clenow top 20", ("cl", 20)), ("Clenow top 20 + SPY filtras", ("cl", 20, 0.001, True))]
if FREQ == "W":
    RUNS = [("12-1 top 10 (sav.)", ("mom", 10)), ("12-1 top 25 (sav.)", ("mom", 25)), ("12-1 top 50 (sav.)", ("mom", 50))]
for lab, kw in RUNS:
    r = backtest(*kw)
    res[lab] = r
    print(f"{lab:30}" + " | ".join(st(r, a, b).ljust(19) for a, b in P))
pd.DataFrame(res).to_pickle(f"{d}/mom_results_{FREQ}.pkl")
