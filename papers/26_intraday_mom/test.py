#!/usr/bin/env python3
"""#26 Dienos vidaus momentum kripto (Gao, Han, Li, Zhou 2018 JFE akcijoms; Wen, Bouri ir kt. 2022 kripto).
Prognozuoja paskutinės dienos valandos (23–24 UTC) grąžą pagal: a) pirmą valandą (00–01), b) dieną iki 23 val. (00–23), c) priešpaskutinę valandą.
Sandoris: paskutinę valandą long, jei prognozė > 0, short – jei < 0 (arba tik long). Valandiniai Binance spot o/c, 8 monetos.
Mokestis 0,05 % į vieną pusę (futures). 2018-01 – 2021-11 ir 2021-11 – 2026-11."""
import os, numpy as np, pandas as pd
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../10_sezoniskumas/data")
S = ["BTC", "ETH", "BNB", "XRP", "ADA", "LINK", "LTC", "TRX"]
def daily(s):
    d = pd.read_pickle(f"{D}/{s}USDT.pkl").set_index("t"); d = d[~d.index.duplicated()]
    d["day"] = d.index.floor("D"); d["hr"] = d.index.hour
    g = d.groupby("day")
    o0 = g.apply(lambda x: x.o[x.hr == 0].iloc[0] if (x.hr == 0).any() else np.nan)
    piv = d.pivot_table(index="day", columns="hr", values=["o", "c"])
    f = pd.DataFrame({"first": piv["c"][0] / piv["o"][0] - 1, "pre": piv["c"][22] / piv["o"][0] - 1,
                      "h22": piv["c"][22] / piv["o"][22] - 1, "last": piv["c"][23] / piv["o"][23] - 1})
    return f.dropna()
F = {s: daily(s) for s in S}
def st(R, a, b):
    R = R[a:b]; e = (1 + R).cumprod(); y = len(R) / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+.1f}%/m. DD {(e / e.cummax() - 1).min() * 100:.0f}%"
for pred in ["first", "pre", "h22"]:
    corr = np.mean([F[s][pred].corr(F[s]["last"]) for s in S])
    for side in ["ls", "long"]:
        for fee in [0.0, 0.0005]:
            out = []
            for s in S:
                p = np.sign(F[s][pred]);
                if side == "long": p = p.clip(lower=0)
                out.append(p * F[s]["last"] - p.abs() * 2 * fee)
            R = pd.concat(out, axis=1).fillna(0).mean(axis=1)
            print(f"{pred:5s} koreliacija {corr:+.3f} | {side:4s} mokestis {fee*100:.2f}%: 2018–21 {st(R, '2018-01-01', '2021-11-08')} | 2021–26 {st(R, '2021-11-08', '2026-11-14')}", flush=True)
