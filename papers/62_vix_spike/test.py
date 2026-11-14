"""62: VIX šuolio pirkimas – A) Connors „VIX Stretches“ (VIX ≥ 5 % virš 10 d. SMA 3 d. iš eilės, SPY > SMA200 -> pirkti, parduoti kai RSI(2) > 65);
B) populiarus „pirk kai VIX > 30/40“ (laikyti N d.); C) VIX/VIX SMA10 > 1,2–1,3 -> laikyti N d. Pirkimas uždarymu, kaštai 0,03 %, laisvi – BIL.
Paleisti: quantconnect-lean/.venv/bin/python papers/62_vix_spike/test.py"""
import os, numpy as np, pandas as pd, yfinance as yf
D = os.path.dirname(os.path.abspath(__file__)); DD = os.path.join(os.path.dirname(D), "59_ibs/data"); FEE = 0.0003
f = f"{D}/vix.csv"
if not os.path.exists(f): yf.download("^VIX", start="2000-01-01", auto_adjust=True, progress=False, multi_level_index=False).to_csv(f)
vix = pd.read_csv(f, index_col=0, parse_dates=True).Close
L = lambda t: pd.read_csv(f"{DD}/{t}.csv", index_col=0, parse_dates=True).Close
bil = L("BIL").pct_change()
def rsi(x, n):
    d = x.diff(); u = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean(); v = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean(); return 100 - 100/(1 + u/v)
def st(x, a, b):
    x = x[a:b].dropna(); e = (1 + x).cumprod(); y = len(x) / 252
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+5.1f}% kr {(e / e.cummax() - 1).min() * 100:3.0f}%"
PER = [("2001", "2012"), ("2013", "2019"), ("2020", "2026")]
def sim(c, ent, ex=None, hold=None):
    pos = np.zeros(len(c)); inp = False; k = 0
    for i in range(len(c)):
        if inp:
            k += 1
            if (ex is not None and ex.iloc[i]) or (hold is not None and k >= hold): inp = False
        if not inp and ent.iloc[i]: inp = True; k = 0
        pos[i] = inp
    return pd.Series(pos, c.index)
print("periodai: 2001–12 | 2013–19 | 2020–26")
for t in ("SPY", "QQQ"):
    c = L(t); v = vix.reindex(c.index).ffill(); r = c.pct_change().fillna(0); cash = bil.reindex(c.index).fillna(0)
    s200 = c.rolling(200).mean(); r2 = rsi(c, 2); vs = v.rolling(10).mean()
    print(f"\n{t} laikyti: " + " | ".join(st(r, a, b) for a, b in PER))
    rules = {"A VIX Stretches (Connors)": (((v > vs * 1.05).rolling(3).sum() == 3) & (c > s200), r2 > 65, None),
             "A be SMA200 filtro": ((v > vs * 1.05).rolling(3).sum() == 3, r2 > 65, None)}
    for lvl in (30, 40):
        for h in (20, 60):
            rules[f"B VIX > {lvl}, laikyti {h} d."] = (v > lvl, None, h)
    for k in (1.2, 1.3):
        for h in (5, 20):
            rules[f"C VIX/SMA10 > {k}, laikyti {h} d."] = (v / vs > k, None, h)
    for nm, (ent, ex, h) in rules.items():
        pos = sim(c, ent, ex, h); p1 = pos.shift(1).fillna(0)
        x = p1 * r + (1 - p1) * cash - pos.diff().abs().fillna(0) * FEE
        print(f"  {nm:32s} " + " | ".join(st(x, a, b) for a, b in PER) + f" | rinkoje {pos.mean()*100:.0f}%, sandorių {int((pos.diff() > 0).sum())}")
