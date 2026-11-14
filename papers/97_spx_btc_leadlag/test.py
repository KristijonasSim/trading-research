"""97: Akcijų → BTC vėlavimas (populiarus „BTC seka Nasdaq“): jei QQQ/SPY dienos grąža (uždarymas 20/21 UTC) > 0, laikyti BTC nuo 21:00 UTC iki kitos dienos 21:00 UTC.
Variantai: QQQ grąža > 0, > +1 %, < −1 % (kontrarinis). BTC valandinės kainos (papers/10_sezoniskumas), 0,1 % mokestis. Paleisti: freqtrade/.venv/bin/python papers/97_spx_btc_leadlag/test.py"""
import os, pandas as pd, numpy as np
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
b = pd.read_pickle(f"{R}/10_sezoniskumas/data/BTCUSDT.pkl"); b = pd.Series(b.c.values, pd.to_datetime(b.t))
b21 = b[b.index.hour == 21]; b21.index = b21.index.normalize()
q = pd.read_csv(f"{R}/59_ibs/data/QQQ.csv", index_col=0, parse_dates=True).Close.pct_change()
fwd = (b21.reindex(q.index).shift(-1) / b21.reindex(q.index) - 1)
df = pd.DataFrame({"q": q, "f": fwd}).dropna(); df = df[df.index >= "2018-01-01"]
def st(x):
    e = (1 + x).cumprod(); y = (x.index[-1] - x.index[0]).days / 365.25; return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+6.1f}% kr {(e / e.cummax() - 1).min() * 100:4.0f}%"
print(f"koreliacija QQQ dienos grąža ~ BTC kitos 24 h: 2018–21 {df.q[:'2021'].corr(df.f[:'2021']):+.3f} | 2022–26 {df.q['2022':].corr(df.f['2022':]):+.3f}")
for nm, m in (("visada (BTC tik prekybos d.)", df.q == df.q), ("QQQ > 0", df.q > 0), ("QQQ > +1 %", df.q > 0.01), ("QQQ < −1 % (kontr.)", df.q < -0.01), ("QQQ < 0", df.q < 0)):
    x = (df.f - 0.002) * m
    print(f"  {nm:28s} 2018–21 {st(x[:'2021'])} | 2022–26 {st(x['2022':])} | dienų {m.mean()*100:.0f}%, vid. {df.f[m].mean()*1e4:+.1f} bp")
