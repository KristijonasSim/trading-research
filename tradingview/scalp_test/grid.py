import sys, itertools, json, numpy as np, pandas as pd
from multiprocessing import Pool
from sim import *
D, name = sys.argv[1], sys.argv[2]
m = lambda s: np.datetime64(s, "m").astype(np.int64)
TR, TE, END = m("2021-03-01"), m("2025-01-01"), m("2026-11-10")
DATA = {}
for tf, tfm in (("5min", 5), ("15min", 15)):
    df = load(D, name, tf); x = indicators(df, 288)
    DATA[tf] = (df, x, (x.medRange / 0.26).clip(0.05, 2).fillna(1).values, *sessions(df, tfm))

def run(cfg):
    tf, km, to, sl, sess, eodx = cfg
    df, x, ka, rth, eod = DATA[tf]
    k = ka * km
    b, s = signals(df, x, k)
    tr = simulate(df, b, s, k, trail_off=to, sl=sl, session=rth if sess else None, eod=eod if eodx else None)
    return dict(tf=tf, km=km, to=to, sl=sl, rth=sess, eod=eodx, train=stats(tr, TR, TE), test=stats(tr, TE, END))

grid = list(itertools.product(["5min", "15min"], [0.6, 1, 1.5, 2, 3], [1.2, 2, 3], [None, 2, 4, 8], [False, True], [False, True]))
with Pool(8) as p:
    res = p.map(run, grid)
json.dump(res, open(f"grid_{name}.json", "w"), default=float)
res = [r for r in res if r["train"]["n"] >= 100]
res.sort(key=lambda r: -r["train"]["cagr"] / max(r["train"]["dd"], 3))
for r in res[:15]:
    print(r["tf"], "km", r["km"], "tp", r["to"], "sl", r["sl"], "rth", r["rth"], "eod", r["eod"], "|TRAIN", {k: r["train"][k] for k in ("n", "win", "cagr", "dd", "pf")}, "|TEST", {k: r["test"][k] for k in ("n", "win", "cagr", "dd", "pf")})
