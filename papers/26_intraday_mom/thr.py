"""#26 papildomai: prekiauti tik kai |dienos grąža iki 23 val.| > slenkstis (0,05 % mokestis)."""
import os
__file__ = os.path.abspath("test.py")
exec(open("test.py").read().split("for pred in")[0])
for thr in [0.02, 0.04, 0.06, 0.08, 0.10]:
    for side in ["ls", "long"]:
        out = []; n = 0
        for s in S:
            x = F[s]["pre"]; p = np.sign(x) * (x.abs() > thr)
            if side == "long": p = p.clip(lower=0)
            n += int(p.abs().sum()); out.append(p * F[s]["last"] - p.abs() * 0.001)
        R = pd.concat(out, axis=1).fillna(0).mean(axis=1)
        print(f"slenkstis {thr*100:.0f}% {side:4s}: 2018–21 {st(R, '2018-01-01', '2021-11-08')} | 2021–26 {st(R, '2021-11-08', '2026-11-14')} | sandorių {n}", flush=True)
