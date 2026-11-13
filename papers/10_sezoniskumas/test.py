#!/usr/bin/env python3
"""#10 Kripto savaitės dienų / valandų sezoniškumas, walk-forward.
Kiekvieniems metams Y: iš VISŲ ankstesnių duomenų (iki Y) apskaičiuojama vidutinė grąža kiekvienam „langeliui“
(valanda 0–23 UTC, savaitės diena 0–6, arba diena×valanda 168). Y metais laikoma moneta tik langeliuose,
kur ankstesnis vidurkis > 0 ir t-stat > T. Mokestis 0,1 % už kiekvieną pirkimą ir pardavimą.
Testas 2020–2026 (kiekvieni metai mokomi tik iš praeities)."""
import sys, numpy as np, pandas as pd
FEE = 0.001
SY = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "LTCUSDT", "XRPUSDT", "ADAUSDT", "TRXUSDT", "LINKUSDT"]


def load(s):
    d = pd.read_pickle(f"data/{s}.pkl").set_index("t")
    r = d.c.pct_change().dropna()          # grąža per valandą, kuri prasideda t-1h
    r.index = r.index - pd.Timedelta(hours=1)   # priskiriama valandai, kurios metu ji uždirbta
    return r


def bins(idx, kind):
    if kind == "valanda": return idx.hour
    if kind == "diena": return idx.day_of_week
    return idx.day_of_week * 24 + idx.hour


def wf(r, kind, T, years=range(2020, 2027)):
    out = []
    for y in years:
        tr = r[r.index.year < y]; te = r[r.index.year == y]
        if len(te) == 0: continue
        g = tr.groupby(bins(tr.index, kind))
        t = g.mean() / (g.std() / np.sqrt(g.count()))
        good = set(t[(g.mean() > 0) & (t > T)].index)
        pos = pd.Series(bins(te.index, kind), te.index).isin(good).astype(float)
        trades = pos.diff().abs().fillna(pos.iloc[0])
        out.append(pos * te - trades * FEE)
    return pd.concat(out) if out else pd.Series(dtype=float)


def st(r):
    eq = (1 + r).cumprod(); yrs = (r.index[-1] - r.index[0]).days / 365.25
    return (eq.iloc[-1] ** (1 / yrs) - 1) * 100, (eq / eq.cummax() - 1).min() * 100


if __name__ == "__main__":
    rows = []; yearly = {}
    for s in SY:
        r = load(s)
        hold = r[r.index.year >= 2020]
        c, d = st(hold); rows.append((s, "laikyti", "-", c, d, 100.0))
        yearly[(s, "laikyti")] = (1 + hold).groupby(hold.index.year).prod() - 1
        for kind in ["valanda", "diena", "diena×valanda"]:
            for T in [0, 1, 2]:
                x = wf(r, kind, T)
                c, d = st(x)
                inv = (x != 0).mean() * 100
                rows.append((s, kind, T, c, d, inv))
                yearly[(s, f"{kind} t>{T}")] = (1 + x).groupby(x.index.year).prod() - 1
    df = pd.DataFrame(rows, columns=["moneta", "langelis", "t>", "%/m", "kritimas %", "laiko rinkoje %"]).round(1)
    pd.set_option("display.width", 200); pd.set_option("display.max_rows", 200)
    txt = df.to_markdown(index=False)
    Y = pd.DataFrame(yearly).T.mul(100).round(1)
    txt += "\n\nMetai 2020–2026 (%):\n\n" + Y.to_markdown()
    print(txt); open("REZULTATAI.txt", "w").write(txt + "\n")
