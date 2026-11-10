"""EI3v2 + E0V1E_DCA3 derinys: po pusę pinigų kiekvienam botui (dvi atskiros sąskaitos).
A) be perbalansavimo; B) kas mėnesį grąžinama į 50/50. Balansas pagal uždarytus sandorius (kaip Freqtrade)."""
import json, zipfile, glob, sys
import pandas as pd

def equity(tag, s):
    z = zipfile.ZipFile(sorted(glob.glob(f"results/combo/{tag}_{s}/*.zip"))[-1])
    n = [x for x in z.namelist() if x.endswith(".json") and not x.endswith("_config.json")][0]
    d = json.loads(z.read(n))["strategy"][s]
    t = pd.DataFrame(d["trades"]); t["close_date"] = pd.to_datetime(t.close_date)
    pnl = t.groupby(t.close_date.dt.floor("D")).profit_abs.sum()
    idx = pd.date_range(d["backtest_start"][:10], d["backtest_end"][:10], tz="UTC")
    bal = 1000 + pnl.reindex(idx, fill_value=0).cumsum()
    return bal.pct_change().fillna(0)

def st(r):
    eq = (1 + r).cumprod(); y = len(r) / 365
    yr = r.groupby(r.index.year).apply(lambda x: round(100 * ((1 + x).prod() - 1)))
    return f"{100*(eq.iloc[-1]**(1/y)-1):5.1f}%/m  kritimas {100*(1-eq/eq.cummax()).max():4.1f}%  metai {dict(yr)}"

out = []
for tag, lab in [("new", "2021-11 – 2026-11 (dabartinis top 10)"), ("old", "2018 – 2021-11 (nematyti, 2018 m. top 9)")]:
    a, b = equity(tag, "EI3v2_tag_cofi_green"), equity(tag, "E0V1E_DCA3")
    ea, eb = (1 + a).cumprod(), (1 + b).cumprod()
    A = ((ea + eb) / 2).pct_change().fillna(0)
    m = a.index.to_period("M")
    B = pd.concat([((1 + a[m == p]).cumprod() + (1 + b[m == p]).cumprod()).div(2).pipe(lambda e: e.pct_change().fillna(e.iloc[0] - 1)) for p in m.unique()])
    out += [f"## {lab}", f"EI3v2 vienas:        {st(a)}", f"E0V1E_DCA3 vienas:   {st(b)}",
            f"50/50 be perbalans.: {st(A)}", f"50/50 kas mėnesį:    {st(B)}",
            f"dienų koreliacija: {a.corr(b):.2f}", ""]
print("\n".join(out))
