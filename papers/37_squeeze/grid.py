"""#37 TTM jautrumas: Keltner daugiklis 1.25–3.0, BTC+ETH ir atskirai, 0,1 % ir 0,15 %."""
import os
__file__ = os.path.abspath("test.py")
exec(open("test.py").read().split("data = {")[0])
data = {s: load(s) for s in ["BTC", "ETH"]}
for kc in [1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 3.0]:
    pos = {s: ttm(data[s], kc) for s in data}
    x = pd.concat([ret(data[s], pos[s]) for s in data], axis=1, sort=True)["2018":].fillna(0).mean(axis=1)
    per = " ".join(f"{s}:{st(ret(data[s], pos[s])['2018':], '2021-11-08', '2026-11-14').split('%')[0]}" for s in data)
    print(f"kc={kc}: {st(x, '2018-01-01', '2021-11-08')} | {st(x, '2021-11-08', '2026-11-14')} | atskirai 2021–26 {per} | rinkoje {pd.concat(pos,axis=1)['2021-11-08':].mean().mean():.0%}", flush=True)
