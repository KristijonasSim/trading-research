"""103: JAV rinkos atidarymo diapazono pramušimas (ORB), BTC/ETH 5m. Diapazonas = pirmos 30 min. po 9:30 NY laiko
(su vasaros laiku). Po to iki 16:00 NY: 5m uždarymas > max -> long, < min -> short (variantas). Stop = kita diapazono pusė
arba vidurys, išėjimas 16:00 NY. Tik darbo dienos. Mokestis 0,1 % ratui. 2018–2021-11 ir 2021-11–2026."""
import pandas as pd, numpy as np, os
D = os.path.expanduser("~/Desktop/trading-research/freqtrade/user_data/data/binance")
FEE = 0.001
def load(c):
    d = pd.read_feather(f"{D}/{c}_USDT-5m.feather")[["date","open","high","low","close"]].set_index("date")
    d.index = d.index.tz_convert("America/New_York"); return d
def run(df, a, b, short, stopmode, orm=30):
    df = df[(df.index >= pd.Timestamp(a, tz="UTC")) & (df.index < pd.Timestamp(b, tz="UTC"))]
    df = df[(df.index.dayofweek < 5)]
    mins = df.index.hour * 60 + df.index.minute
    df = df[(mins >= 570) & (mins < 960)]; mins = df.index.hour * 60 + df.index.minute
    trades = []
    for day, g in df.groupby(df.index.date):
        m = g.index.hour * 60 + g.index.minute
        rng = g[m < 570 + orm]; rest = g[m >= 570 + orm]
        if len(rng) < orm // 5 or len(rest) < 10: continue
        hi, lo = rng.high.max(), rng.low.min(); mid = (hi + lo) / 2
        pos = 0
        for t, row in rest.iterrows():
            if pos == 0:
                if row.close > hi: pos, ent, stop = 1, row.close, (lo if stopmode == "min" else mid)
                elif short and row.close < lo: pos, ent, stop = -1, row.close, (hi if stopmode == "min" else mid)
                elif row.close < lo or row.close > hi: break
                continue
            if pos == 1 and row.low <= stop: trades.append((t, stop / ent - 1 - FEE)); pos = 0; break
            if pos == -1 and row.high >= stop: trades.append((t, ent / stop - 1 - FEE)); pos = 0; break
        if pos != 0: trades.append((t, (row.close / ent - 1) * pos - FEE))
    if not trades: return None
    s = pd.Series(dict(trades)); eq = (1 + s).cumprod(); yrs = (pd.Timestamp(b) - pd.Timestamp(a)).days / 365.25
    return (eq.iloc[-1] ** (1 / yrs) - 1) * 100, ((eq / eq.cummax()) - 1).min() * 100, len(s), (s > 0).mean() * 100, s.groupby(s.index.year).apply(lambda x: (1 + x).prod() - 1).mul(100).round(0).astype(int).to_dict()
out = ["# 103 JAV atidarymo ORB – rezultatai\n", "| Moneta | Laikotarpis | Variantas | %/m. | Max kritimas | Sandoriai | Laimi | Metai |", "|---|---|---|---|---|---|---|---|"]
for c in ["BTC", "ETH"]:
    df = load(c); print(c, df.index[0], df.index[-1], flush=True)
    for a, b in [("2018-01-01", "2021-11-08"), ("2021-11-08", "2026-11-08")]:
        for short in [False, True]:
            for sm in ["min", "mid"]:
                for orm in [15, 30, 60]:
                    r = run(df, a, b, short, sm, orm)
                    if r: out.append(f"| {c} | {a[:7]}–{b[:7]} | {'long+short' if short else 'tik long'}, stop={sm}, {orm} min | {r[0]:+.1f} | {r[1]:.0f} % | {r[2]} | {r[3]:.0f} % | {r[4]} |")
open("rezultatai_raw.md", "w").write("\n".join(out) + "\n"); print("\n".join(out))
