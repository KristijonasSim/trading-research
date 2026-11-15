"""105: Savaitgalio diapazono pramušimas pirmadienį. Savaitgalio (šešt. 00:00 – sekm. 24:00 UTC) max/min.
Pirmadienį–antradienį: jei 1h uždarymas > savaitgalio max -> long (stop = savaitgalio min arba vidurys), išeiti penktadienio 23:00
arba stop. Simetriškai short (tik futures varianto). Mokestis 0,1 % ratui. Tikrinama 2018–2021-11 (spot) ir 2021-11–2026."""
import pandas as pd, numpy as np, os
D = os.path.expanduser("~/Desktop/trading-research/freqtrade/user_data/data/binance")
FEE = 0.001
def load(c):
    d = pd.read_feather(f"{D}/{c}_USDT-1h.feather")[["date","open","high","low","close"]].set_index("date"); d.index = d.index.tz_localize(None); return d
def run(df, a, b, short, stopmode, entry_days=(0, 1)):
    df = df[(df.index >= a) & (df.index < b)]
    trades = []
    wk = df.index.to_period("W-SUN")
    for p, g in df.groupby(wk):
        we = g[g.index.dayofweek >= 5]
        if len(we) < 40: continue
        hi, lo = we.high.max(), we.low.min(); mid = (hi + lo) / 2
        nxt = df[(df.index > we.index[-1]) & (df.index < we.index[-1] + pd.Timedelta(days=6))]
        pos = 0
        for t, row in nxt.iterrows():
            if pos == 0 and t.dayofweek in entry_days:
                if row.close > hi: pos, ent, stop = 1, row.close, (lo if stopmode == "min" else mid)
                elif short and row.close < lo: pos, ent, stop = -1, row.close, (hi if stopmode == "min" else mid)
                continue
            if pos == 1 and row.low <= stop: trades.append((t, stop / ent - 1 - FEE)); pos = 0; break
            if pos == -1 and row.high >= stop: trades.append((t, ent / stop - 1 - FEE)); pos = 0; break
            if pos != 0 and t.dayofweek == 4 and t.hour == 23:
                trades.append((t, (row.close / ent - 1) * pos - FEE)); pos = 0; break
    if not trades: return None
    s = pd.Series(dict(trades)); eq = (1 + s).cumprod(); yrs = (pd.Timestamp(b) - pd.Timestamp(a)).days / 365.25
    return (eq.iloc[-1] ** (1 / yrs) - 1) * 100, ((eq / eq.cummax()) - 1).min() * 100, len(s), (s > 0).mean() * 100, s.groupby(s.index.year).apply(lambda x: (1 + x).prod() - 1).mul(100).round(0).astype(int).to_dict()
out = ["# 105 Savaitgalio diapazono pramušimas – rezultatai\n", "| Moneta | Laikotarpis | Variantas | %/m. | Max kritimas | Sandoriai | Laimi | Metai |", "|---|---|---|---|---|---|---|---|"]
for c in ["BTC", "ETH"]:
    df = load(c)
    for a, b in [("2018-01-01", "2021-11-08"), ("2021-11-08", "2026-11-08")]:
        for short in [False, True]:
            for sm in ["min", "mid"]:
                r = run(df, a, b, short, sm)
                if r: out.append(f"| {c} | {a[:7]}–{b[:7]} | {'long+short' if short else 'tik long'}, stop={sm} | {r[0]:+.1f} | {r[1]:.0f} % | {r[2]} | {r[3]:.0f} % | {r[4]} |")
open("rezultatai_raw.md", "w").write("\n".join(out) + "\n"); print("\n".join(out))
