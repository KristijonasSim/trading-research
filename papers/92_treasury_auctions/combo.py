"""#61 + #92 kartu: TLT long paskutines 5 mėnesio prekybos d. ARBA 5 d. po aukciono; short 5 d. prieš aukcioną (jei ne mėnesio pabaiga); kitu metu BIL. 1x ir sintetinis 3x."""
import json, os, numpy as np, pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(D)
A = json.load(open(f"{D}/data/note.json")) + json.load(open(f"{D}/data/bond.json"))
days = pd.DatetimeIndex(sorted({pd.to_datetime(x["competitiveAuctionCloseDate"]) for x in A if x.get("competitiveAuctionCloseDate") and x["originalSecurityTerm"] in ("10-Year", "20-Year", "30-Year")}))
L = lambda t: pd.read_csv(f"{R}/59_ibs/data/{t}.csv", index_col=0, parse_dates=True).Close
c = L("TLT"); c = c[c.index >= "2004-01-01"]; r = c.pct_change().fillna(0); cash = L("BIL").pct_change().reindex(c.index).fillna(0)
idx = c.index; left = pd.Series(idx, idx).groupby(idx.to_period("M")).transform(lambda s: np.arange(len(s))[::-1])
me = (left < 5).astype(float); after = pd.Series(0.0, idx); before = pd.Series(0.0, idx)
for k in idx.searchsorted(days):
    if k < len(idx): after.iloc[k + 1:k + 6] = 1; before.iloc[max(0, k - 4):k + 1] = 1
def st(x, a, b):
    x = x[a:b]; e = (1 + x).cumprod(); n = len(x) / 252; return f"{(e.iloc[-1] ** (1 / n) - 1) * 100:+5.1f}% kr {(e / e.cummax() - 1).min() * 100:3.0f}%"
PER = [("2004", "2012"), ("2013", "2019"), ("2020", "2026")]
print("periodai: 2004–12 | 2013–19 | 2020–26 | 2013–26")
for lev in (1, 3):
    rr = lev * r - (lev - 1) * cash - (0.0095 / 252 if lev > 1 else 0)
    for nm, pos in (("#61 mėn. pabaiga", me), ("#92 po long / prieš short", after - before), ("abu: long (pab. ARBA po), short prieš", ((me + after) > 0).astype(float) - before * (me == 0))):
        pos = pos.clip(-1, 1); x = pos * rr + (1 - pos.abs()) * cash - pos.diff().abs().fillna(0) * 0.0003 * lev
        print(f"{lev}x {nm:38s} " + " | ".join(st(x, a, b) for a, b in PER) + f" | {st(x, '2013', '2027')} | rinkoje {pos.abs().mean()*100:.0f}%")
