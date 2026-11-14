"""70: Azijos sesijos diapazono pramušimas (populiarus forex/kripto teiginys): diapazonas 00:00–08:00 UTC; nuo 08:00 stop orderiai ties aukštuma (long)
ir žemuma (short); stop – priešinga diapazono riba arba vidurys; uždarymas 21:00 UTC. Vienas sandoris per dieną (pirmas pramušimas).
Užpildymas: max(atidarymas, lygis) – jei žvakė atsidaro už lygio, pildoma atidarymu. Jei toje pačioje žvakėje paliečiamas stop – stop.
Binance 1h (freqtrade, 2018–2026), mokestis 0,05 % (perp)/pusė. Paleisti: freqtrade/.venv/bin/python papers/70_asian_range/test.py"""
import os, numpy as np, pandas as pd
R = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "freqtrade/user_data/data/binance")
def run(d, side, stop_mode, fee):
    d = d.set_index("date"); out = {}
    for day, g in d.groupby(d.index.floor("D")):
        if len(g) < 22: continue
        a = g[g.index.hour < 8]; s = g[(g.index.hour >= 8) & (g.index.hour < 21)]
        hi, lo = a.high.max(), a.low.min(); mid = (hi + lo) / 2; ret = 0.0
        for t, b in s.iterrows():
            L = side in ("long", "both") and b.high >= hi; S = side in ("short", "both") and b.low <= lo
            if L and not S:
                e = max(b.open, hi); st_ = lo if stop_mode == "range" else mid; rest = s[s.index > t]
                hit = (b.low <= st_) or (rest.low <= st_).any()
                ret = (st_ / e - 1) if hit else (s.close.iloc[-1] / e - 1); break
            if S and not L:
                e = min(b.open, lo); st_ = hi if stop_mode == "range" else mid; rest = s[s.index > t]
                hit = (b.high >= st_) or (rest.high >= st_).any()
                ret = (1 - st_ / e) if hit else (1 - s.close.iloc[-1] / e); break
            if L and S: break      # abi pusės toje pačioje žvakėje – praleidžiama
        out[day] = ret - (2 * fee if ret != 0 else 0)
    return pd.Series(out)
def st(x, a, b):
    x = x[(x.index >= pd.Timestamp(a, tz="UTC")) & (x.index < pd.Timestamp(b, tz="UTC"))]; e = (1 + x).cumprod(); y = len(x) / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+6.1f}% kr {(e / e.cummax() - 1).min() * 100:4.0f}%"
PER = [("2018-01-01", "2022-01-01"), ("2022-01-01", "2027-01-01")]
print("periodai: 2018–21 | 2022–26")
for c in ("BTC", "ETH", "SOL"):
    d = pd.read_feather(f"{R}/{c}_USDT-1h.feather")
    for side in ("long", "short", "both"):
        for sm in ("range", "mid"):
            x = run(d, side, sm, 0.0005)
            print(f"{c} {side:5s} stop {sm:5s}: {' | '.join(st(x, a, b) for a, b in PER)} | sandorių d. {(x != 0).mean()*100:.0f}%, laimi {(x[x != 0] > 0).mean()*100:.0f}%", flush=True)
