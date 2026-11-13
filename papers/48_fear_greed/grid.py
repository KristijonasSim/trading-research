"""#48 trendo varianto jautrumas: slenkstis 50–80, vėlavimas 1–3 d., BTC/ETH/BTC+ETH, 0,1 % ir 0,2 %."""
import os
__file__ = os.path.abspath("test.py")
exec(open("test.py").read().split("for s in")[0])
P = {s: load(s)["2018-02-01":] for s in ["BTC", "ETH"]}
for lag in [1, 2, 3]:
    print(f"vėlavimas {lag} d.:")
    for th in [50, 55, 60, 65, 70, 75, 80]:
        cells = []; rr = []
        for s, p in P.items():
            r = p.pct_change().fillna(0); g = fg.reindex(p.index).ffill()
            w = (g > th).astype(float).shift(lag).fillna(0); x = w * r - w.diff().abs().fillna(0) * 0.001; rr.append(x)
            cells.append(f"{s} {st(x, '2018-02-01', '2021-11-08')} | {st(x, '2021-11-08', '2026-11-14')}")
        x = pd.concat(rr, axis=1).mean(axis=1); y = (1 + x["2021-11-08":]).groupby(x["2021-11-08":].index.year).prod() - 1
        n = int((((fg.reindex(P['BTC'].index).ffill() > th).astype(int).diff() == 1)['2021-11-08':]).sum())
        print(f"  FGI>{th}: BTC+ETH {st(x, '2018-02-01', '2021-11-08')} | {st(x, '2021-11-08', '2026-11-14')} | " + " ".join(f"{k}:{v*100:+.0f}" for k, v in y.items()) + f" | įėjimų BTC {n} || " + " || ".join(cells), flush=True)
