"""95: Turtle (Dennis/Eckhardt; Faith 2007) S1 20/10 ir S2 55/20 Donchian pramušimas ant alts10 ir top 10 2018 m. monetų (išgyvenusiųjų patikra),
1d, long-only spot 0,1 %. Signalas uždarymu (uždarymas > N d. maksimumas be šios dienos), išėjimas uždarymas < M d. minimumas. Kiekviena moneta lygiu svoriu.
Paleisti: freqtrade/.venv/bin/python papers/95_turtle_alts/test.py"""
import os, numpy as np, pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = f"{ROOT}/freqtrade/user_data/data/binance"; B = f"{ROOT}/papers/data/binance_1d"
def load(c):
    f = f"{R}/{c}_USDT-1d.feather"
    if os.path.exists(f): d = pd.read_feather(f); return pd.Series(d.close.values, d.date.dt.tz_localize(None))
    b = pd.read_csv(f"{B}/{c}USDT.csv"); return pd.Series(b.c.values, pd.to_datetime(b.t, unit="ms"))
def turtle(c, n, m):
    hi, lo = c.rolling(n).max().shift(), c.rolling(m).min().shift(); pos = np.zeros(len(c)); cur = 0
    for i in range(len(c)):
        if cur and c.iloc[i] < lo.iloc[i]: cur = 0
        if not cur and c.iloc[i] > hi.iloc[i]: cur = 1
        pos[i] = cur
    pos = pd.Series(pos, c.index); r = c.pct_change().fillna(0); return pos.shift(1).fillna(0) * r - pos.diff().abs().fillna(0) * 0.001
def st(x, a, b):
    x = x[a:b]; e = (1 + x).cumprod(); y = len(x) / 365.25; return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+6.1f}% kr {(e / e.cummax() - 1).min() * 100:4.0f}%"
PER = [("2018-06-01", "2022-01-01"), ("2022-01-01", "2027-01-01")]
U = {"alts10": "XRP BNB SOL DOGE ADA TRX LINK AVAX LTC DOT".split(), "2018 top 10 (be BTC/ETH)": "XRP BCC EOS LTC ADA XLM IOTA TRX NEO XMR".split()}
print("periodai: 2018-06–21 | 2022–26")
for nm, coins in U.items():
    ok = [c for c in coins if os.path.exists(f"{R}/{c}_USDT-1d.feather") or os.path.exists(f"{B}/{c}USDT.csv")]
    px = {c: load(c) for c in ok}
    h = pd.concat([p.pct_change() for p in px.values()], axis=1, sort=True).fillna(0).mean(axis=1)
    print(f"{nm} ({len(ok)}: {' '.join(ok)}) laikyti: {' | '.join(st(h, a, b) for a, b in PER)}")
    for n, m in ((20, 10), (55, 20), (100, 50)):
        x = pd.concat([turtle(p, n, m) for p in px.values()], axis=1, sort=True).fillna(0).mean(axis=1)
        print(f"   Turtle {n}/{m}: {' | '.join(st(x, a, b) for a, b in PER)}")
# išgyvenusiųjų patikra #94 SimpleBollinger (BB 20,2) toms pačioms visatoms
def sboll(c, n=20, k=2.0):
    m = c.rolling(n).mean(); up = m + k * c.rolling(n).std(); pos = np.zeros(len(c)); cur = 0
    for i in range(len(c)):
        if cur and c.iloc[i] < m.iloc[i]: cur = 0
        if not cur and c.iloc[i] > up.iloc[i]: cur = 1
        pos[i] = cur
    pos = pd.Series(pos, c.index); r = c.pct_change().fillna(0); return pos.shift(1).fillna(0) * r - pos.diff().abs().fillna(0) * 0.001
print("\nSimpleBollinger (#94) išgyvenusiųjų patikra:")
for nm, coins in U.items():
    ok = [c for c in coins if os.path.exists(f"{R}/{c}_USDT-1d.feather") or os.path.exists(f"{B}/{c}USDT.csv")]
    x = pd.concat([sboll(load(c)) for c in ok], axis=1, sort=True).fillna(0).mean(axis=1)
    print(f"   {nm}: {' | '.join(st(x, a, b) for a, b in PER)}")
# 2021-11 top 20 be BTC/ETH (įskaitant vėliau žlugusias LUNA, FTT), 2021-11-08 – 2026-11
T21 = "BNB SOL ADA XRP DOT DOGE AVAX LUNA SHIB MATIC LTC LINK UNI ALGO BCH ATOM FTT TRX".split()
def load_csv(c):
    b = pd.read_csv(f"{B}/{c}USDT.csv"); s = pd.Series(b.c.values, pd.to_datetime(b.t, unit="ms"))
    if c == "LUNA": s = s[:"2022-05-13"]                      # po žlugimo – kita moneta (LUNA 2.0)
    return s
P21 = {c: load_csv(c) for c in T21}
h = pd.concat([p.pct_change() for p in P21.values()], axis=1, sort=True).fillna(0).mean(axis=1)
print(f"\n2021-11 top 20 be BTC/ETH ({len(T21)} monetų, su LUNA/FTT), 2021-11-08 – 2026-11:")
def st2(x): x = x["2021-11-08":]; e = (1 + x).cumprod(); y = len(x) / 365.25; return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+6.1f}% kr {(e / e.cummax() - 1).min() * 100:4.0f}%"
print(f"   laikyti: {st2(h)}")
for n, m in ((20, 10), (55, 20)): print(f"   Turtle {n}/{m}: {st2(pd.concat([turtle(p, n, m) for p in P21.values()], axis=1, sort=True).fillna(0).mean(axis=1))}")
print(f"   SimpleBollinger 20/2: {st2(pd.concat([sboll(p) for p in P21.values()], axis=1, sort=True).fillna(0).mean(axis=1))}")
