#!/usr/bin/env python3
"""#15 patikra su Binance USDT-M perp kontraktais: ar žemo vol long-short realiai įgyvendinamas.
Visata: perp kontraktai (amžius ≥ 60 d.), top N pagal 30 d. apyvartą. Kas savaitę: long 20 % mažiausio
30 d. volatilumo, short 20 % didžiausio. Funding: long moka, short gauna (tikra istorija). Mokestis 0,05 % / 0,1 %.
Ribotumas: seniai išregistruotų perp'ų Binance API nebeduoda (short pusei tai konservatyvu)."""
import glob, os, sys, numpy as np, pandas as pd
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data")
px, qv, fu = {}, {}, {}
for f in glob.glob(f"{D}/perp_1d/*.csv"):
    d = pd.read_csv(f)
    if len(d) < 90: continue
    s = os.path.basename(f)[:-4]; i = pd.to_datetime(d.t, unit="ms")
    px[s] = pd.Series(d.c.values, i); qv[s] = pd.Series(d.qv.values, i)
    g = f"{D}/funding/{s}.csv"
    if os.path.exists(g):
        x = pd.read_csv(g)
        if len(x): fu[s] = pd.Series(x.rate.values, pd.to_datetime(x.t, unit="ms").dt.floor("D")).groupby(level=0).sum()
P = pd.DataFrame(px).sort_index(); V = pd.DataFrame(qv).reindex(P.index); FU = pd.DataFrame(fu).reindex(P.index).fillna(0)
R = P.pct_change(fill_method=None); age = P.notna().cumsum(); liq = V.rolling(30, min_periods=20).mean()
vol = R.rolling(30, min_periods=20).std()


def run(topn=50, q=0.2, fee=0.0005, step=7, mode="ls", funding=True):
    eq = [1.0]; dates = [P.index[0]]
    for i in range(70, len(P) - 1, step):
        ok = (age.iloc[i] >= 60) & P.iloc[i].notna() & vol.iloc[i].notna() & liq.iloc[i].notna()
        uni = liq.iloc[i][ok].nlargest(topn).index
        if len(uni) < 20: continue
        sc = vol.iloc[i][uni].sort_values(); k = max(1, int(len(sc) * q))
        lo, hi = sc.index[:k], sc.index[-k:]
        w = pd.Series(0.0, P.columns)
        if mode in ("ls",): w[lo] = 0.5 / k; w[hi] = -0.5 / k
        if mode == "short": w[hi] = -1 / k
        if mode == "long": w[lo] = 1 / k
        if mode == "btc_short": w["BTCUSDT"] = 0.5; w[hi] = -0.5 / k
        nz = w[w != 0].index
        j = min(i + step, len(P) - 1)
        rr = R.iloc[i + 1:j + 1][nz].fillna(0); path = (1 + rr).cumprod()
        f = FU.iloc[i + 1:j + 1][nz] if funding else 0 * rr
        val = 1 + (path - 1).mul(w[nz]).sum(axis=1) - (f * path.shift(1).fillna(1)).mul(w[nz]).sum(axis=1).cumsum()
        e0 = eq[-1] * (1 - 2 * fee * w.abs().sum())   # supaprastinta: visa pozicija atidaroma ir uždaroma kas savaitę
        eq += list(e0 * val.values); dates += list(rr.index)
    return pd.Series(eq, dates)


def st(e, a, b):
    e = e[(e.index >= a) & (e.index < b)]; y = (e.index[-1] - e.index[0]).days / 365.25
    yr = e.resample("YE").last(); yr = pd.concat([pd.Series([e.iloc[0]], [e.index[0]]), yr]).pct_change().dropna()
    return round(((e.iloc[-1] / e.iloc[0]) ** (1 / y) - 1) * 100, 1), round((e / e.cummax() - 1).min() * 100, 1), {k.year: round(v * 100) for k, v in yr.items()}


rows = []
for name, kw in [("LS top50, 0,05 %", {}), ("LS top50, 0,1 %", dict(fee=0.001)), ("LS top50 be funding", dict(funding=False)),
                 ("LS top30", dict(topn=30)), ("LS top100", dict(topn=100)), ("LS 10 %", dict(q=0.1)), ("LS kas mėn.", dict(step=28)),
                 ("Tik short aukšto vol", dict(mode="short")), ("Tik long žemo vol", dict(mode="long")), ("BTC long + short aukšto vol", dict(mode="btc_short"))]:
    e = run(**kw)
    a = st(e, "2020-03-01", "2022-01-01"); b = st(e, "2022-01-01", "2026-12-01")
    rows.append(f"| {name} | {a[0]:+.1f} | {a[1]:.0f} | {b[0]:+.1f} | {b[1]:.0f} | {b[2]} |"); print(rows[-1], flush=True)
md = "| Variantas (perp) | 2020-03–2021 %/m | kritimas | 2022–26 %/m | kritimas | metai |\n|---|---|---|---|---|---|\n" + "\n".join(rows)
open("REZULTATAI_perp.txt", "w").write(md + "\n")
