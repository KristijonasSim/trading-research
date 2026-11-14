"""#48 patikra: tas pats FGI trendo signalas ant alts10 (lygūs svoriai), slenkstis 55/60/65, vėlavimas 1 d., 0,1 %."""
import os
__file__ = os.path.abspath("test.py")
exec(open("test.py").read().split("for s in")[0])
A = ["XRP", "BNB", "SOL", "DOGE", "ADA", "TRX", "LINK", "AVAX", "LTC", "DOT"]
P = pd.DataFrame({s: load(s) for s in A}).sort_index()["2018-02-01":]; R = P.pct_change(fill_method=None).fillna(0)
g = fg.reindex(P.index).ffill()
print(f"alts10 laikyti: {st(R.mean(axis=1), '2018-02-01', '2021-11-08')} | {st(R.mean(axis=1), '2021-11-08', '2026-11-14')}")
for th in [55, 60, 65]:
    w = (g > th).astype(float).shift(1).fillna(0)
    x = w * R.mean(axis=1) - w.diff().abs().fillna(0) * 0.001
    y = (1 + x["2021-11-08":]).groupby(x["2021-11-08":].index.year).prod() - 1
    print(f"FGI>{th}: {st(x, '2018-02-01', '2021-11-08')} | {st(x, '2021-11-08', '2026-11-14')} | " + " ".join(f"{k}:{v*100:+.0f}" for k, v in y.items()))
