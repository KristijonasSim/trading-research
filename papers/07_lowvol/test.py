#!/usr/bin/env python3
"""#7 Žemo volatilumo / betting-against-beta S&P 500 akcijose (Frazzini, Pedersen 2014; Baker ir kt. 2011).
Kas mėnesį iš tuo metu indekse esančių akcijų (fja05680/sp500 sudėtis, Yahoo kainos):
 - mažiausio 1 m. volatilumo 50 / 100 akcijų, lygūs svoriai;
 - mažiausios 1 m. betos (prieš SPY) 100 akcijų;
 - BAB long-short: žemos betos pusė (svertu iki betos 1) minus aukštos betos pusė (iki betos 1).
Palyginimas: to paties akcijų rinkinio lygiavertis krepšelis (vienodas išgyvenusiųjų iškraipymas), SPY, realūs ETF SPLV, USMV.
Mokestis 0,1 % nuo apyvartos. Ribotumas: Yahoo neturi ~35–50 % iki 2011 iš indekso išėjusių akcijų."""
import numpy as np, pandas as pd
C = pd.read_pickle("data/closes.pkl")
H = pd.read_csv("data/hist.csv", parse_dates=["date"]).set_index("date").tickers.str.split(",")
etf = {k: C.pop(k) for k in ["SPY", "SPLV", "USMV"] if k in C}
# kainos tik tuo laikotarpiu, kai akcija buvo indekse (+1 m. prieš betai/vol): tikeriai perpanaudojami
span = {}
for dt, ts in H.items():
    for x in ts:
        x = x.replace(".", "-"); a, b = span.get(x, (dt, dt)); span[x] = (min(a, dt), max(b, dt))
for x in C.columns:
    a, b = span.get(x, (None, None))
    if b is not None and b == H.index[-1]: b = pd.Timestamp("2100-01-01")
    if a is None: C[x] = np.nan; continue
    C.loc[(C.index < a - pd.Timedelta(days=400)) | (C.index > b + pd.Timedelta(days=40)), x] = np.nan
spy = etf["SPY"]; R = C.pct_change(fill_method=None); rs = spy.pct_change()
vol = R.rolling(252, min_periods=200).std() * np.sqrt(252)
beta = R.rolling(252, min_periods=200).cov(rs).div(rs.rolling(252, min_periods=200).var(), axis=0)
days = C.index[C.index >= "2001-01-01"]
me = pd.Series(days, days).groupby(days.to_period("M")).last().values
FEE = 0.001


def members(dt):
    return [t.replace(".", "-") for t in H[H.index <= dt].iloc[-1]]


W = {k: pd.DataFrame(0.0, C.index, C.columns) for k in ["lowvol50", "lowvol100", "lowbeta100", "bab", "ew"]}
for dt in me[:-1]:
    m = [t for t in members(dt) if t in C.columns and not np.isnan(C.at[dt, t]) and not np.isnan(vol.at[dt, t])]
    v = vol.loc[dt, m].sort_values(); b = beta.loc[dt, m].dropna().sort_values()
    rows = {"lowvol50": pd.Series(1 / 50, v.index[:50]), "lowvol100": pd.Series(1 / 100, v.index[:100]),
            "lowbeta100": pd.Series(1 / 100, b.index[:100]), "ew": pd.Series(1 / len(m), m)}
    lo, hi = b.index[:len(b) // 2], b.index[len(b) // 2:]
    bl, bh = max(b[lo].mean(), 0.5), max(b[hi].mean(), 0.5)   # svertas ne daugiau 2x
    rows["bab"] = pd.concat([pd.Series(1 / bl / len(lo), lo), pd.Series(-1 / bh / len(hi), hi)])
    for k, w in rows.items():
        W[k].loc[dt, w.index] = w.values
nxt = pd.Series(me[1:], me[:-1])


def bt(w):
    w = w.loc[me[:-1]].reindex(C.index).ffill().fillna(0)
    held = w.shift(1).fillna(0)
    # svoriai drift'ina tarp perbalansavimų – supaprastinta: kasdien perbalansuota iki tikslinių svorių, mokestis tik mėnesio pradžioje
    turn = w.loc[me[:-1]].diff().abs().sum(axis=1).reindex(C.index).fillna(0).shift(1).fillna(0)
    return ((held * R.fillna(0)).sum(axis=1) - turn * FEE)[days]


S = {k: bt(w) for k, w in W.items()}
S["SPY"] = rs[days].fillna(0)
for k in ["SPLV", "USMV"]:
    S[k] = etf[k].pct_change()[days]


def st(r, a, b):
    r = r[a:b].dropna()
    if len(r) < 200: return ["–"] * 4
    eq = (1 + r).cumprod(); y = len(r) / 252
    return [f"{(eq.iloc[-1] ** (1 / y) - 1) * 100:+.1f}", f"{(eq / eq.cummax() - 1).min() * 100:.0f}",
            f"{r.mean() / r.std() * np.sqrt(252):.2f}", f"{r.std() * np.sqrt(252) * 100:.0f}"]


per = [("2001", "2013"), ("2014", "2026"), ("2012", "2026")]
names = {"lowvol50": "Žemas vol, 50 akc.", "lowvol100": "Žemas vol, 100 akc.", "lowbeta100": "Žema beta, 100 akc.",
         "bab": "BAB long-short", "ew": "Visos (lygiavertis)", "SPY": "SPY", "SPLV": "SPLV (realus ETF)", "USMV": "USMV (realus ETF)"}
out = "| Strategija | " + " | ".join(f"{a}–{b} %/m | kritimas | Sharpe | vol" for a, b in per) + " |\n|" + "---|" * 13 + "\n"
for k, n in names.items():
    out += f"| {n} | " + " | ".join(" | ".join(st(S[k], a, b)) for a, b in per) + " |\n"
yr = pd.DataFrame({names[k]: (1 + S[k]["2014":]).groupby(S[k]["2014":].index.year).prod() - 1 for k in names}).mul(100).round(1)
out += "\nMetai 2014–2026 (%):\n\n" + yr.to_markdown()
print(out); open("REZULTATAI.txt", "w").write(out + "\n")
