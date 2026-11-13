#!/usr/bin/env python3
"""Quantpedia nemokamos strategijos, kurias galima patikrinti su viešais duomenimis.
Vienodos taisyklės: 0,05 % mokestis už kiekvieną pirkimą/pardavimą, laisvi pinigai = BIL (iki 2007 – 0 %).
Rezultatai dviem laikotarpiais: iki 2015 (autorių laikas) ir 2016–2026 (vėliau, „nematyta“).
Paleisti: ../quantconnect-lean/.venv/bin/python test.py
"""
from pathlib import Path
import numpy as np, pandas as pd

R = Path(__file__).resolve().parent
FEE = 0.0005
T = ["SPY", "QQQ", "TLT", "IEF", "EFA", "EEM", "GLD", "DBC", "VNQ", "BIL", "CL=F"]


def load():
    f = R / "data/px.pkl"
    if f.exists():
        return pd.read_pickle(f)
    import yfinance as yf
    d = yf.download(T, start="1993-01-01", end="2026-11-13", auto_adjust=True, progress=False)
    d.to_pickle(f)
    return d


D = load()
C, O = D["Close"], D["Open"]
spy = C.SPY.dropna()
idx = spy.index
cash = C.BIL.reindex(idx).pct_change().fillna(0)
r_spy = spy.pct_change().fillna(0)


def run_weights(w, rets):
    """w: dienos svoriai (nustatyti dienos pabaigoje, galioja nuo kitos dienos)."""
    w = w.reindex(idx).ffill().fillna(0)
    held = w.shift(1).fillna(0)
    turn = held.diff().abs().sum(axis=1) if isinstance(held, pd.DataFrame) else held.diff().abs()
    if isinstance(held, pd.DataFrame):
        g = (held * rets).sum(axis=1) + (1 - held.sum(axis=1)).clip(lower=0) * cash
    else:
        g = held * rets + (1 - held) * cash
    return g - turn.fillna(0) * FEE


def stats(r, a, b):
    r = r[a:b]
    eq = (1 + r).cumprod()
    yrs = len(r) / 252
    cagr = eq.iloc[-1] ** (1 / yrs) - 1
    dd = (eq / eq.cummax() - 1).min()
    return f"{100 * cagr:5.1f} %/m., kritimas {100 * -dd:4.0f} %"


S = {}
# 0041 Turn of the month: pirkti paskutinės mėn. dienos uždaryme, laikyti 3 pirmas kito mėn. dienas
m = pd.Series(idx.to_period("M"), index=idx)
last = m != m.shift(-1)
dnum = m.groupby(m).cumcount() + 1
S["0041 Mėnesio pradžia (SPY)"] = run_weights((last | (dnum <= 2)).astype(float), r_spy)

# 0083 Prieš šventes: laikyti dieną prieš JAV biržos šventę (darbo dienų tarpas)
nxt = pd.Series(idx, index=idx).shift(-1)
gap = (nxt - pd.Series(idx, index=idx)).dt.days
pre = ((gap > 1) & ~((idx.dayofweek == 4) & (gap == 3))) | ((idx.dayofweek == 4) & (gap > 3))
# svoris nustatomas dienos prieš šventę išvakarėse -> laikoma pačią dieną prieš šventę
S["0083 Prieš šventes (SPY)"] = run_weights(pd.Series(pre, index=idx).shift(-1).fillna(False).astype(float), r_spy)

# 0102 Opcionų galiojimo savaitė: laikyti nuo penktadienio prieš 3-iąjį mėn. penktadienį iki jo
fri3 = (idx.dayofweek == 4) & (idx.day >= 15) & (idx.day <= 21)
wk = pd.Series(False, index=idx)
for d in idx[fri3]:
    wk[(idx > d - pd.Timedelta(days=7)) & (idx <= d)] = True
S["0102 Opcionų savaitė (SPY)"] = run_weights(wk.shift(-1).fillna(False).astype(float), r_spy)

# 0031 Sezoniškumas: lapkritis–balandis SPY, gegužė–spalis pinigai
S["0031 Lapkritis–balandis (SPY)"] = run_weights(pd.Series(np.isin(idx.month, [10, 11, 12, 1, 2, 3]) & 1, index=idx)
                                                 .where(~((idx.month == 10) & ~last), 0).astype(float), r_spy)

# 0661 Naktis: pirkti uždaryme, parduoti atidaryme (kasdien 2 sandoriai)
on = (O.SPY / C.SPY.shift(1) - 1).reindex(idx).fillna(0) - 2 * FEE
S["0661 Tik naktis (SPY)"] = on

# 0044 Paired switching: ketvirčio pabaigoje laikyti SPY arba TLT, kurio ketvirtis buvo geresnis
q = pd.Series(idx.to_period("Q"), index=idx)
qe = idx[q != q.shift(-1)]
w = pd.DataFrame(0.0, index=idx, columns=["SPY", "TLT"])
for d in qe:
    p = C.loc[:d, ["SPY", "TLT"]].dropna()
    if len(p) < 64:
        continue
    r63 = p.iloc[-1] / p.iloc[-64] - 1
    w.loc[d, :] = 0; w.loc[d, r63.idxmax()] = 1
w = w.loc[qe].reindex(idx).ffill().fillna(0)
rets2 = C[["SPY", "TLT"]].reindex(idx).pct_change().fillna(0)
S["0044 SPY/TLT kas ketvirtį"] = run_weights(w, rets2)

# 0096 Nafta: jei praeito mėn. naftos grąža neigiama -> SPY, kitaip pinigai
me = idx[last.values]
oil = C["CL=F"].reindex(idx).ffill()
sig = (oil.loc[me].pct_change() < 0).astype(float)
S["0096 Nafta krito -> SPY"] = run_weights(sig.reindex(idx).ffill().fillna(0), r_spy)

# 0118 Laiko eilučių momentum: 8 ETF, kiekvienas laikomas (1/8), jei 12 mėn. grąža > 0
A = ["SPY", "EFA", "EEM", "TLT", "IEF", "GLD", "DBC", "VNQ"]
cm = C[A].reindex(idx).ffill().loc[me]
w = ((cm / cm.shift(12) - 1) > 0).astype(float) / len(A)
S["0118 Trendas 8 ETF"] = run_weights(w.reindex(idx).ffill().fillna(0), C[A].reindex(idx).pct_change().fillna(0))

S["Pirkti ir laikyti SPY"] = r_spy

lines = ["| Strategija | iki 2015 | 2016–2026 |", "|---|---|---|"]
for k, r in S.items():
    lines.append(f"| {k} | {stats(r, '1994', '2015')} | {stats(r, '2016', '2026')} |")

# Kripto: 0753 BTC nakties sezoniškumas ir 0701 perbalansavimo premija
B = pd.read_feather(R.parent / "freqtrade/user_data/data/binance/BTC_USDT-1h.feather").set_index("date").close
E = pd.read_feather(R.parent / "freqtrade/user_data/data/binance/ETH_USDT-1h.feather").set_index("date").close
br = B.pct_change().dropna()
hr = br.groupby(br.index.hour).mean()
ins = br[:"2023-12-31"]; oos = br["2024-01-01":]
best = ins.groupby(ins.index.hour).mean().nlargest(3).index.tolist()
sel = oos[np.isin(oos.index.hour, best)]
nb = (np.isin(oos.index.hour, best).astype(int))
trades = (np.diff(np.r_[0, nb]) != 0).sum()
eq_sel = (1 + sel).prod() * (1 - 0.001) ** trades
eq_bh = (1 + oos).prod()
yrs = (oos.index[-1] - oos.index[0]).days / 365.25
crypto = [f"- 0753 BTC geriausios 3 valandos (UTC) pagal 2021-11..2023: {best}; 2024–2026 jas laikant: "
          f"x{eq_sel:.2f} su kaštais (x{(1 + sel).prod():.2f} be), pirkti ir laikyti x{eq_bh:.2f}"]
d = pd.concat([B, E], axis=1, keys=["B", "E"]).resample("1D").last().dropna()
dr = d.pct_change().dropna()
reb = (dr.mean(axis=1) - 0.001 * (dr.B - dr.E).abs() / 2)
bh = (d / d.iloc[0]).mean(axis=1)
crypto.append(f"- 0701 BTC/ETH 50/50 kasdien perbalansuojant: x{(1 + reb).prod():.2f}, nelaikant balanso x{bh.iloc[-1]:.2f}")

out = "\n".join(["# Quantpedia strategijų patikra", "", *lines, "", "## Kripto", *crypto])
(R / "REZULTATAI.md").write_text(out)
print(out)
