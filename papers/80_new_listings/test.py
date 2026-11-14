"""80: Naujų listingų nuosmukis („short new Binance listings“, low float / high FDV; taip pat IPO ilgalaikio atsilikimo analogas, Ritter 1991).
Visos Binance spot USDT poros (su išregistruotomis). Monetos „amžius“ = dienos nuo pirmos žvakės. Portfelis kasdien: lygiais svoriais visos monetos,
kurių amžius tarp a ir b dienų (įeinama kitą dieną po to, kai amžius ≥ a). Short versija: −1 × šis portfelis (be funding/skolinimo kaštų – optimistiška),
mokestis 0,1 % nuo apyvartos. Taip pat vidutinė kumuliatyvi grąža pagal amžių (event study) ir BTC palyginimas. Paleisti: python3 papers/80_new_listings/test.py"""
import glob, os
import numpy as np, pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(D)
px = {}
for f in glob.glob(f"{R}/data/binance_1d/*.csv"):
    d = pd.read_csv(f)
    if len(d) < 30: continue
    px[os.path.basename(f)[:-4]] = pd.Series(d.c.values, pd.to_datetime(d.t, unit="ms"))
P = pd.DataFrame(px).sort_index(); first = P.apply(lambda s: s.first_valid_index())
P = P.loc[:, first > pd.Timestamp("2018-06-01")]          # tikri nauji listingai (ne 2017 pradinis sąrašas)
print("listingų:", P.shape[1])
age = P.notna().cumsum().where(P.notna()); Rt = P.pct_change(fill_method=None)
btc = pd.read_csv(f"{R}/data/binance_1d/BTCUSDT.csv"); btc = pd.Series(btc.c.values, pd.to_datetime(btc.t, unit="ms")).reindex(P.index).pct_change().fillna(0)
# event study: vidutinė grąža pagal amžiaus savaitę, palyginti su BTC
print("vid. kumuliatyvi grąža nuo 2-os dienos (mediana per monetas) ir perteklinė prieš BTC:")
for N in (7, 30, 90, 180, 365):
    rr, ex = [], []
    for c in P.columns:
        s = P[c].dropna()
        if len(s) <= N + 1: continue
        rr.append(s.iloc[N + 1] / s.iloc[1] - 1); b = btc[s.index[1]:s.index[N + 1]]; ex.append((s.iloc[N + 1] / s.iloc[1]) / (1 + b).prod() - 1)
    print(f"  {N:3d} d.: mediana {np.median(rr)*100:+6.1f} %, vid. {np.mean(rr)*100:+6.1f} %, perteklinė mediana {np.median(ex)*100:+6.1f} %, n={len(rr)}")
def st(x, a, b):
    x = x[a:b].fillna(0); e = (1 + x).cumprod(); y = len(x) / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+6.1f}% kr {(e / e.cummax() - 1).min() * 100:4.0f}%"
PER = [("2019-01-01", "2022-01-01"), ("2022-01-01", "2024-01-01"), ("2024-01-01", "2027-01-01")]
print("\nperiodai: 2019–21 | 2022–23 | 2024–26")
print(f"BTC laikyti                      " + " | ".join(st(btc, a, b) for a, b in PER))
for a, b in ((2, 30), (7, 60), (7, 90), (30, 180)):
    m = ((age >= a) & (age < b)).shift(1, fill_value=False)
    w = m.div(m.sum(axis=1), axis=0).fillna(0); n = m.sum(axis=1)
    long = (w * Rt.fillna(0)).sum(axis=1); turn = w.diff().abs().sum(axis=1).fillna(0) * 0.001
    short = -long - turn; hedged = -(long - btc) - turn
    print(f"amžius {a:3d}–{b:3d} d.: long {' | '.join(st(long - turn, x, y) for x, y in PER)} | short {' | '.join(st(short, x, y) for x, y in PER)} | short+BTC long {' | '.join(st(hedged, x, y) for x, y in PER)} | vid. monetų {n['2019':].mean():.0f}")
