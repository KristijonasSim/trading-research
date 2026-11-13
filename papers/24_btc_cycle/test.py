#!/usr/bin/env python3
"""#24 Populiarūs ilgalaikiai BTC indikatoriai (tik kaina, Yahoo BTC-USD nuo 2014):
 - Mayer daugiklis (Trace Mayer): kaina / SMA200; laikyti, kai < 2,4 (parduoti virš 2,4); variantas – pirkti tik < 1,0, parduoti > 2,4.
 - Pi Cycle Top (Philip Swift): parduoti, kai SMA111 > 2 × SMA350; pirkti atgal, kai kaina > SMA350.
 - 200 sav. vidurkis: pirkti, kai kaina < 200W SMA × 1,2, laikyti iki Mayer > 2,4.
Mokestis 0,1 %, pinigai 0 %. Periodai: 2015–2021, 2021-11–2026-11."""
import os, numpy as np, pandas as pd, yfinance as yf
f = "data/btc.pkl"
if not os.path.exists(f):
    yf.download("BTC-USD", start="2014-01-01", end="2026-11-13", auto_adjust=True, progress=False).to_pickle(f)
X = pd.read_pickle(f); c = X["Close"].iloc[:, 0] if isinstance(X["Close"], pd.DataFrame) else X["Close"]
r = c.pct_change().fillna(0); FEE = 0.001
sma200 = c.rolling(200).mean(); mm = c / sma200; s111 = c.rolling(111).mean(); s350 = c.rolling(350).mean(); w200 = c.rolling(1400).mean()
def statef(enter, exit_):
    pos = np.zeros(len(c)); p = 0
    for i in range(len(c)):
        if p == 0 and enter.iloc[i]: p = 1
        elif p == 1 and exit_.iloc[i]: p = 0
        pos[i] = p
    return pd.Series(pos, c.index)
S = {"Laikyti BTC": pd.Series(1.0, c.index),
     "Mayer < 2,4": (mm < 2.4).astype(float).where(sma200.notna(), 1.0),
     "Mayer: pirkti < 1,0, parduoti > 2,4": statef(mm < 1.0, mm > 2.4),
     "Pi Cycle Top išėjimas": statef(c > s350, s111 > 2 * s350).where(s350.notna(), 1.0),
     "200W ×1,2 pirkti, Mayer > 2,4 parduoti": statef(c < w200 * 1.2, mm > 2.4),
     "Kaina > SMA200": (c > sma200).astype(float)}
def st(x, a, b):
    x = x[a:b]; eq = (1 + x).cumprod(); y = (x.index[-1] - x.index[0]).days / 365.25
    return f"{(eq.iloc[-1] ** (1 / y) - 1) * 100:+.1f} ({(eq / eq.cummax() - 1).min() * 100:.0f})"
rows = []
for k, s in S.items():
    pos = s.shift(1).fillna(0); x = pos * r - pos.diff().abs().fillna(0) * FEE
    rows.append(f"| {k} | {pos['2015':].mean()*100:.0f} % | {st(x, '2015-01-01', '2021-11-08')} | {st(x, '2021-11-08', '2026-11-08')} | {st(x, '2015-01-01', '2026-11-08')} |"); print(rows[-1])
open("REZULTATAI.txt", "w").write("| Strategija | rinkoje | 2015–2021-11 %/m (kritimas) | 2021-11–2026-11 | 2015–2026 |\n|---|---|---|---|---|\n" + "\n".join(rows) + "\n")
