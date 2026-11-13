#!/usr/bin/env python3
"""#9 Kripto porų prekyba (Fil, Kristoufek 2020): kointegracijos ir atstumo metodai, 1h.
Kas savaitę: formavimas = paskutinės N valandų; atrenkama top K porų (kointegracija: Engle-Granger DF t < -3,37;
atstumas: mažiausia normalizuotų kainų kvadratų suma). Prekyba kitą savaitę: |z| > Z įeiti, z kerta 0 – išeiti,
|z| > 4 – stop, savaitės gale uždaroma. Signalas valandos uždarymu, sandoris kitos valandos kaina.
Mokestis kiekvienai kojai. Long-short (short = futures, funding neįskaičiuotas)."""
import itertools, sys, numpy as np, pandas as pd

SY = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "LTCUSDT", "XRPUSDT", "ADAUSDT", "TRXUSDT", "LINKUSDT"]
P = pd.concat({s: pd.read_pickle(f"../10_sezoniskumas/data/{s}.pkl").set_index("t").c for s in SY}, axis=1)
P = P["2019-02-01":].ffill()
L = np.log(P); R = P.pct_change().fillna(0)
PAIRS = list(itertools.combinations(SY, 2))


def df_t(e):
    de = np.diff(e); el = e[:-1] - e[:-1].mean()
    b = (el * de).sum() / (el ** 2).sum()
    res = de - b * el
    se = np.sqrt((res ** 2).sum() / (len(de) - 2) / (el ** 2).sum())
    return b / se


def run(method="coint", form=720, K=5, Z=2.0, fee=0.001, step=168):
    n = len(P); pnl = np.zeros(n); lv = L.values; rv = R.values; col = {s: i for i, s in enumerate(SY)}
    for st in range(form, n - 1, step):
        end = min(st + step, n - 1)
        F = lv[st - form:st]
        cand = []
        for a, b in PAIRS:
            x, y = F[:, col[b]], F[:, col[a]]
            if method == "coint":
                beta = np.cov(y, x)[0, 1] / np.var(x, ddof=1)
                e = y - beta * x
                t = df_t(e)
                if t < -3.37: cand.append((t, a, b, beta, e.mean(), e.std()))
            else:
                ny = y - y[0]; nx = x - x[0]; e = ny - nx
                cand.append(((e ** 2).sum(), a, b, 1.0, e.mean(), e.std()))
        cand.sort(key=lambda c: c[0])
        for _, a, b, beta, mu, sd in cand[:K]:
            ia, ib = col[a], col[b]
            base_y, base_x = (lv[st - form, ia], lv[st - form, ib]) if method == "dist" else (0, 0)
            wa, wb = 1 / (1 + abs(beta)), abs(beta) / (1 + abs(beta))
            pos = 0
            for t in range(st, end):
                if pos != 0:   # pozicija laikoma valandą t -> t+1
                    pnl[t + 1] += pos * (wa * rv[t + 1, ia] - np.sign(beta) * wb * rv[t + 1, ib]) / K
                z = ((lv[t, ia] - base_y) - beta * (lv[t, ib] - base_x) - mu) / sd
                new = pos
                if pos == 0 and abs(z) > Z and abs(z) < 4: new = -np.sign(z)
                elif pos != 0 and (pos * z >= 0 or abs(z) > 4 or t == end - 1): new = 0
                if new != pos:
                    pnl[t + 1] -= abs(new - pos) * fee / K   # abi kojos: wa + wb = 1
                    pos = new
    return pd.Series(pnl, P.index)


def st(r):
    eq = (1 + r).cumprod(); y = (r.index[-1] - r.index[0]).days / 365.25
    return round((eq.iloc[-1] ** (1 / y) - 1) * 100, 1), round((eq / eq.cummax() - 1).min() * 100, 1)


rows = []; yearly = {}
for m in ["coint", "dist"]:
    for form in [720, 2160]:
        for Z in [2.0, 2.5]:
            for fee in [0.001, 0.0005, 0.0002]:
                r = run(m, form, 5, Z, fee)
                a, b = r[:"2021-12-31"], r["2022-01-01":]
                rows.append((m, form // 24, Z, fee * 100, *st(a), *st(b)))
                yearly[f"{m} {form//24}d z{Z} fee{fee*100:.2f}"] = (1 + r).groupby(r.index.year).prod() - 1
                print(rows[-1], flush=True)
df = pd.DataFrame(rows, columns=["metodas", "formavimas d.", "z", "mokestis %", "2019–21 %/m", "kritimas", "2022–26 %/m", "kritimas "])
txt = df.to_markdown(index=False) + "\n\nMetai (%):\n\n" + pd.DataFrame(yearly).T.mul(100).round(1).to_markdown()
open("REZULTATAI.txt", "w").write(txt + "\n"); print(txt)
