"""#50 papildomai: signalas iš QQQ/SPY, prekiaujama TQQQ/UPRO (MOC), kaštai 0,05 %."""
import os
__file__ = os.path.abspath("test.py")
exec(open("test.py").read().split("cash = C")[0])
cash = C["BIL"].pct_change().fillna(0)
for base, lev in [("QQQ", "TQQQ"), ("SPY", "UPRO")]:
    c = C[base]; r2 = rsi(c, 2); s200 = c.rolling(200).mean(); s5 = c.rolling(5).mean(); rl = C[lev].pct_change().fillna(0)
    print(f"{lev} laikyti: 2010–15 {st(rl, '2010-03', '2016')} | 2016–26 {st(rl, '2016', '2027')}")
    for nm, ent, ex in [("RSI2<10", (r2 < 10) & (c > s200), c > s5), ("kaup.RSI2<35", (r2 + r2.shift() < 35) & (c > s200), r2 > 65), ("RSI2<10 be SMA200", r2 < 10, c > s5)]:
        pos = np.zeros(len(c)); inp = False
        for i in range(len(c)):
            if inp and ex.iloc[i]: inp = False
            elif not inp and ent.iloc[i]: inp = True
            pos[i] = inp
        pos = pd.Series(pos, c.index); p1 = pos.shift(1).fillna(0)
        x = p1 * rl + (1 - p1) * cash - pos.diff().abs().fillna(0) * 0.0005
        y = (1 + x["2016":]).groupby(x["2016":].index.year).prod() - 1
        print(f"  {nm}: 2010–15 {st(x, '2010-03', '2016')} | 2016–26 {st(x, '2016', '2027')} | " + " ".join(f"{k}:{v*100:+.0f}" for k, v in y.items()), flush=True)
