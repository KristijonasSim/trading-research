#!/usr/bin/env python3
"""#46 3Commas stiliaus DCA botas (populiarūs viešai skelbiami nustatymai, pvz., „TA Presets“ / Reddit r/3commas):
įėjimas: RSI(14, 5m) < 30 (arba iškart, „ASAP“); bazinis orderis B, apsauginiai (SO) kas dev % žemiau su volume scale v ir step scale s;
uždarymas: TP % virš vidutinės kainos. Be stop-loss. Kiekviena moneta savo kapitalo dalis (1/12), max visų SO suma telpa į dalį.
5m high/low/close 2021-11 – 2026-11 (freqtrade duomenys), mokestis 0,1 %. 12 monetų: BTC, ETH + alts10."""
import numpy as np, pandas as pd
F = "../../freqtrade/user_data/data/binance/"
S = ["BTC", "ETH", "XRP", "BNB", "SOL", "DOGE", "ADA", "TRX", "LINK", "AVAX", "LTC", "DOT"]
def rsi(c, n=14):
    d = np.diff(c, prepend=c[0]); up = pd.Series(np.clip(d, 0, None)).ewm(alpha=1/n, adjust=False).mean().values
    dn = pd.Series(np.clip(-d, 0, None)).ewm(alpha=1/n, adjust=False).mean().values; return 100 - 100 / (1 + up / (dn + 1e-12))
def bot(df, tp=0.015, dev=0.02, n_so=5, vs=1.5, ss=1.2, entry="rsi", fee=0.001):
    h, l, c = df.high.values, df.low.values, df.close.values; r = rsi(c)
    w = np.array([1.0] + [vs ** k for k in range(1, n_so + 1)]); w = w / w.sum()   # viso kapitalo dalys
    lv = np.cumsum([0] + [dev * ss ** k for k in range(n_so)])                       # nuokrypiai nuo įėjimo
    cash = 1.0; qty = 0.0; cost = 0.0; filled = 0; entry_px = 0; eq = np.empty(len(c)); deals = 0
    for t in range(1, len(c)):
        if filled == 0:
            if entry == "asap" or r[t-1] < 30:
                entry_px = c[t-1]; q = cash * w[0] / entry_px; qty = q; cost = q * entry_px * (1 + fee); filled = 1; cash0 = cash
        else:
            while filled <= n_so and l[t] <= entry_px * (1 - lv[filled]):
                px = entry_px * (1 - lv[filled]); q = cash0 * w[filled] / px; qty += q; cost += q * px * (1 + fee); filled += 1
            avg = cost / qty
            if h[t] >= avg * (1 + tp):
                cash = cash0 - cost + qty * avg * (1 + tp) * (1 - fee); qty = 0; cost = 0; filled = 0; deals += 1
        eq[t] = (cash0 - cost + qty * c[t]) if filled else cash
    eq[0] = 1.0
    return pd.Series(eq, df.index), deals
def st(e):
    d = e.resample("D").last(); y = (d.index[-1] - d.index[0]).days / 365.25
    yr = pd.concat([d.iloc[:1], d.resample("YE").last()]).pct_change().dropna()
    return f"{((d.iloc[-1]/d.iloc[0])**(1/y)-1)*100:+.1f}%/m. DD {(d/d.cummax()-1).min()*100:.0f}% | " + " ".join(f"{k.year}:{v*100:+.0f}" for k, v in yr.items())
data = {s: pd.read_feather(f"{F}{s}_USDT-5m.feather").set_index("date")["2021-11-08":"2026-11-08"] for s in S}
hold = pd.concat([d.close / d.close.iloc[0] for d in data.values()], axis=1).ffill().mean(axis=1)
print("12 monetų laikyti:", st(hold), flush=True)
for kw in [dict(), dict(tp=0.01), dict(tp=0.03), dict(dev=0.03, ss=1.3, n_so=6), dict(entry="asap"), dict(dev=0.05, n_so=4, vs=2.0)]:
    out = [bot(data[s], **kw) for s in S]
    e = pd.concat([o[0] for o in out], axis=1).ffill().mean(axis=1)
    print(f"{kw or 'numatyta (TP 1,5 %, SO 5 kas 2 %, ×1,5/×1,2, RSI<30)'}: {st(e)} | sandorių {sum(o[1] for o in out)}", flush=True)
