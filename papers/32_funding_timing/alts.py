"""#32 patikra kitomis monetomis (alts10 perp), tie patys parametrai: N=3, slenkstis 0,01 %/d.; taip pat N=2/5 ir 0,005/0,015."""
import os
__file__ = os.path.abspath("test.py")
exec(open("test.py").read().split("data = {")[0])
A = ["XRP", "BNB", "SOL", "DOGE", "ADA", "TRX", "LINK", "AVAX", "LTC", "DOT"]
data = {}
for s in A:
    try: data[s] = load(s)
    except Exception as e: print(s, "nėra", e)
def ret2(df, pos, fee=0.0005):
    p = pos.shift(1).fillna(0); r = df.c.pct_change().fillna(0)
    return p * r - p * df.f - p.diff().abs().fillna(0) * fee
hold = pd.concat([ret2(d, pd.Series(1.0, d.index)) for d in data.values()], axis=1).fillna(0).mean(axis=1)
print(f"alts10 perp laikyti: 2020–21 {st(hold, '2020-06-01', '2021-11-08')} | 2021–26 {st(hold, '2021-11-08', '2026-11-14')}")
for N in [2, 3, 5]:
    for th in [0.00005, 0.0001, 0.00015]:
        out = {s: ret2(d, (d.f.rolling(N).mean() < th).astype(float)) for s, d in data.items()}
        R = pd.concat(out.values(), axis=1).fillna(0).mean(axis=1)
        y = (1 + R["2021-11-08":]).groupby(R["2021-11-08":].index.year).prod() - 1
        per = " ".join(f"{s}:{((1+r['2021-11-08':]).prod()**(365.25/len(r['2021-11-08':]))-1)*100:+.0f}" for s, r in out.items())
        print(f"N={N} th={th*100:.3f}: 2020–21 {st(R, '2020-06-01', '2021-11-08')} | 2021–26 {st(R, '2021-11-08', '2026-11-14')} | " + " ".join(f"{k}:{v*100:+.0f}" for k, v in y.items()) + f"\n   monetos 2021–26: {per}", flush=True)
