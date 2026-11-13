import test as T, pandas as pd
T.FEE = 0.0
rows=[]
for s in T.SY:
    r = T.load(s); h = r[r.index.year >= 2020]
    for kind in ["valanda", "diena×valanda"]:
        for t in [1, 2]:
            x = T.wf(r, kind, t); inv = (x != 0)
            # palyginimas: vidutinė grąža rinkoje vs visų valandų vidurkis
            rows.append((s, kind, t, round(x[inv].mean()*1e4, 2), round(h.mean()*1e4, 2), round(T.st(x)[0], 1)))
print(pd.DataFrame(rows, columns=["moneta","langelis","t>","bp/val. rinkoje","bp/val. visos","%/m be mokesčio"]).to_markdown(index=False))
