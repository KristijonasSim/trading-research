#!/usr/bin/env python3
"""#43 Halloween indikatorius / „Sell in May“ (Bouman, Jacobsen 2002 AER; Jacobsen, Zhang 2018): akcijos lapkr.–bal., vasarą (geg.–spal.) BIL arba IEF.
Variantai su QQQ, TQQQ (3x tik žiemą). Kaštai 0,05 %. 2005–2015 ir 2016–2026. Taip pat BTC (kripto).""" 
import os, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__))
C = pd.read_csv(f"{H}/../../etf-rotation/data/close.csv", index_col=0, parse_dates=True)
def st(x, a, b, n=252):
    x = x[a:b].dropna(); e = (1 + x).cumprod(); y = len(x) / n
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+.1f}%/m. DD {(e / e.cummax() - 1).min() * 100:.0f}%"
win = pd.Series(C.index.month.isin([11, 12, 1, 2, 3, 4]).astype(float), C.index).shift(1).fillna(0)
for t in ["SPY", "QQQ", "TQQQ", "IWM"]:
    r = C[t].pct_change().fillna(0)
    print(f"{t} laikyti: 2005–15 {st(r, '2005', '2015')} | 2016–26 {st(r, '2016', '2026')}")
    for alt in ["BIL", "IEF"]:
        ra = C[alt].pct_change().fillna(0)
        x = win * r + (1 - win) * ra - win.diff().abs().fillna(0) * 0.0005
        print(f"  {t} žiemą / {alt} vasarą: 2005–15 {st(x, '2005', '2015')} | 2016–26 {st(x, '2016', '2026')}")
d = pd.read_csv(f"{H}/../data/binance_1d/BTCUSDT.csv"); p = pd.Series(d.c.values, pd.to_datetime(d.t, unit="ms")); r = p.pct_change().fillna(0)
w = pd.Series(p.index.month.isin([11, 12, 1, 2, 3, 4]).astype(float), p.index).shift(1).fillna(0)
x = w * r - w.diff().abs().fillna(0) * 0.001
print(f"BTC žiemą: 2018–21 {st(x, '2018', '2021-11-08', 365)} | 2021–26 {st(x, '2021-11-08', '2026-11-14', 365)} (laikyti {st(r, '2021-11-08', '2026-11-14', 365)})")
