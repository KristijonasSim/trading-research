"""69: Fibonacci „golden pocket“ (populiarus TA teiginys): po patvirtinto kilimo bangos (žemuma L -> aukštuma H) pirkti ties 0,618 atatranka,
stop ties 0,786 (arba 1,0), tikslas H (arba 1,272 pratęsimas). Lūžio taškai (pivot) patvirtinami tik po k žvakių iš abiejų pusių – be žvilgsnio į ateitį.
Įėjimas limit orderiu, jei žvakės žemuma pasiekia lygį; jei toje pačioje žvakėje paliestas ir stop – skaičiuojamas stop (konservatyviai).
Binance 4h ir 1d (freqtrade duomenys 2017-11 – 2026-11), mokestis 0,1 %/pusė, viena pozicija vienu metu, 100 % kapitalo.
Paleisti: freqtrade/.venv/bin/python papers/69_fib_golden_pocket/test.py"""
import os, numpy as np, pandas as pd
R = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "freqtrade/user_data/data/binance")
FEE = 0.001
def sim(d, k, entry_f, stop_f, tp_f):
    h, l, c = d.high.values, d.low.values, d.close.values; n = len(d)
    eq = np.ones(n); cap = 1.0; trades = []
    lastL = lastH = None   # (indeksas, kaina) patvirtinti
    setup = None; pos = None
    for i in range(2 * k, n):
        j = i - k        # kandidatas patvirtinamas dabar
        if h[j] == h[j - k:i + 1].max(): lastH = (j, h[j])
        if l[j] == l[j - k:i + 1].min(): lastL = (j, l[j])
        if pos is None and lastL and lastH and lastL[0] < lastH[0] and lastH[1] > lastL[1] * 1.03:
            rng = lastH[1] - lastL[1]
            setup = dict(H=lastH[1], entry=lastH[1] - entry_f * rng, stop=lastH[1] - stop_f * rng, tp=lastL[1] + tp_f * rng, id=lastH[0])
        if pos is not None:
            if l[i] <= pos["stop"]: px = pos["stop"]; done = True
            elif h[i] >= pos["tp"]: px = pos["tp"]; done = True
            else: done = False
            if done:
                ret = px / pos["entry"] * (1 - FEE) ** 2 - 1; cap *= 1 + ret; trades.append((d.date.iloc[i], ret)); pos = None; setup = None; lastH = None
        elif setup is not None and i > setup["id"] + k:
            if h[i] > setup["H"]: setup = None; lastH = None           # nauja aukštuma be atatrankos – laukiam naujos bangos
            elif l[i] <= setup["entry"]:
                pos = dict(setup)
                if l[i] <= pos["stop"]:                                  # ta pati žvakė – stop
                    ret = pos["stop"] / pos["entry"] * (1 - FEE) ** 2 - 1; cap *= 1 + ret; trades.append((d.date.iloc[i], ret)); pos = None; setup = None; lastH = None
        mark = cap if pos is None else cap * c[i] / pos["entry"]
        eq[i] = mark
    return pd.Series(eq, d.date), pd.DataFrame(trades, columns=["t", "r"])
def st(e, a, b):
    e = e[(e.index >= pd.Timestamp(a, tz="UTC")) & (e.index < pd.Timestamp(b, tz="UTC"))]; e = e / e.iloc[0]; y = (e.index[-1] - e.index[0]).days / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+6.1f}% kr {(e / e.cummax() - 1).min() * 100:4.0f}%"
PER = [("2018-01-01", "2022-01-01"), ("2022-01-01", "2027-01-01")]
print("periodai: 2018–21 | 2022–26")
coins = "BTC ETH XRP BNB SOL DOGE ADA TRX LINK AVAX LTC DOT".split()
for tf in ("4h", "1d"):
    for k in ((5, 10) if tf == "4h" else (3, 5)):
        for ef, sf, tp in ((0.618, 0.786, 1.0), (0.618, 1.0, 1.0), (0.618, 0.786, 1.272), (0.5, 0.786, 1.0)):
            res = []; allt = []
            for c in coins:
                f = f"{R}/{c}_USDT-{tf}.feather"
                if not os.path.exists(f): continue
                d = pd.read_feather(f); e, t = sim(d, k, ef, sf, tp); res.append(e.pct_change().fillna(0).rename(c)); allt.append(t)
            port = (1 + pd.concat(res, axis=1).fillna(0).mean(axis=1)).cumprod()
            T = pd.concat(allt); win = (T.r > 0).mean() * 100
            btce = (1 + res[0]).cumprod()
            print(f"{tf} k={k:2d} įėj {ef} stop {sf} tikslas {tp}: 12 monetų {' | '.join(st(port, a, b) for a, b in PER)} | BTC {' | '.join(st(btce, a, b) for a, b in PER)} | sandorių {len(T)}, laimi {win:.0f}%, vid. {T.r.mean()*100:+.2f}%", flush=True)
