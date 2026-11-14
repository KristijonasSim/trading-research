"""81 papildymas: ta pati BTC halvingo ciklo taisyklė (500/550 d.) ETH ir alts10 (Binance 1d) – ar ciklas bendras visai rinkai."""
import json, os
import pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(D)
H = pd.to_datetime(["2012-11-28", "2016-07-09", "2020-05-11", "2024-04-20", "2028-04-15"])
def load(c): b = pd.read_csv(f"{R}/data/binance_1d/{c}USDT.csv"); return pd.Series(b.c.values, pd.to_datetime(b.t, unit="ms"))
def st(x, a, b):
    x = x[a:b]; e = (1 + x).cumprod(); y = len(x) / 365.25; return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+6.1f}% kr {(e / e.cummax() - 1).min() * 100:4.0f}%"
rows_h, rows_s = {}, {}
for c in "ETH XRP BNB SOL DOGE ADA TRX LINK AVAX LTC DOT".split():
    p = load(c); r = p.pct_change().shift(-1).fillna(0); pos = pd.Series(0.0, p.index)
    for h in H: pos[(p.index >= h - pd.Timedelta(days=500)) & (p.index < h + pd.Timedelta(days=550))] = 1
    s = r * pos - pos.diff().abs().fillna(0) * 0.001
    if c == "ETH": print(f"ETH laikyti 2018–20 {st(r, '2018', '2021')} | 2021–26 {st(r, '2021', '2027')} || ciklas {st(s, '2018', '2021')} | {st(s, '2021', '2027')}")
    else: rows_h[c] = r; rows_s[c] = s
H_ = pd.DataFrame(rows_h).fillna(0).mean(axis=1); S_ = pd.DataFrame(rows_s).fillna(0).mean(axis=1)
print(f"alts10 laikyti 2018–20 {st(H_, '2018', '2021')} | 2021–26 {st(H_, '2021', '2027')} || ciklas {st(S_, '2018', '2021')} | {st(S_, '2021', '2027')}")
