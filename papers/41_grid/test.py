#!/usr/bin/env python3
"""#41 Spot grid botas (Binance / Pionex / KuCoin „Spot Grid“ produktas, aritmetinis tinklelis).
Pradžioje intervalas kaina ±R, N lygių; pusė kapitalo monetoje pagal lygius virš kainos (kaip tikras grid: perkama žemiau, parduodama vienu lygiu aukščiau).
Kai kaina išeina iš intervalo ir ten išbūna 1 d., grid perstatomas aplink naują kainą (realizuojant esamą būseną). 5m high/low (freqtrade 5m duomenys 2017-08 – 2026-11),
mokestis 0,1 % (spot) / 0,02 % (maker su BNB nuolaida, VIP). Lyginama su laikymu."""
import numpy as np, pandas as pd
F = "../../freqtrade/user_data/data/binance/"
def grid(df, R=0.15, N=40, fee=0.001):
    h, l, c = df.high.values, df.low.values, df.close.values
    cash, coin = 1000.0, 0.0
    def setup(p, cash, coin):
        tot = cash + coin * p; lv = np.linspace(p * (1 - R), p * (1 + R), N + 1)
        per = tot / N   # kiekvienam tarpui
        hold = np.array([lv[i] >= p for i in range(N)])   # tarpas i (lv[i]..lv[i+1]) „užpildytas“ jei virš kainos -> turi monetą parduoti ties lv[i+1]
        coin_new = sum(per / lv[i] for i in range(N) if hold[i]); cash_new = tot - coin_new * p
        cost = abs(coin_new - coin) * p * fee
        return lv, hold, per, cash_new - cost, coin_new
    lv, hold, per, cash, coin = setup(c[0], cash, coin); out_since = None; eq = np.zeros(len(c)); resets = 0
    for t in range(len(c)):
        for i in range(N):   # pirkimai žemyn, pardavimai aukštyn
            if not hold[i] and l[t] <= lv[i]:
                q = per / lv[i]; cash -= per * (1 + fee); coin += q; hold[i] = True
            elif hold[i] and h[t] >= lv[i + 1]:
                q = per / lv[i]; cash += q * lv[i + 1] * (1 - fee); coin -= q; hold[i] = False
        eq[t] = cash + coin * c[t]
        out = c[t] < lv[0] or c[t] > lv[-1]
        if out:
            out_since = t if out_since is None else out_since
            if t - out_since >= 288:
                lv, hold, per, cash, coin = setup(c[t], cash, coin); out_since = None; resets += 1
        else: out_since = None
    return pd.Series(eq, df.index), resets
def st(e):
    y = (e.index[-1] - e.index[0]).days / 365.25; d = e.resample("D").last()
    yr = d.resample("YE").last(); yr = pd.concat([d.iloc[:1], yr]).pct_change().dropna()
    return f"{((e.iloc[-1]/e.iloc[0])**(1/y)-1)*100:+.1f}%/m. DD {(d/d.cummax()-1).min()*100:.0f}% | " + " ".join(f"{k.year}:{v*100:+.0f}" for k, v in yr.items())
for s in ["BTC", "ETH"]:
    df = pd.read_feather(f"{F}{s}_USDT-5m.feather").set_index("date")
    print(f"{s} laikyti: {st(df.close / df.close.iloc[0] * 1000)}", flush=True)
    for R, N in [(0.10, 20), (0.15, 40), (0.30, 60)]:
        for fee in [0.001, 0.0002]:
            e, rs = grid(df, R, N, fee)
            print(f"  {s} ±{R:.0%} {N} lygių mok. {fee*100:.2f}%: {st(e)} | perstatymų {rs}", flush=True)
