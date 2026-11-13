"""#32 jautrumas: A variantas (long kai N d. vid. funding < slenkstis), N × slenkstis, BTC ir ETH atskirai, mokestis 0,05 / 0,1 %."""
import os
__file__ = os.path.abspath("test.py")
exec(open("test.py").read().split("hold = ")[0])
def ret2(df, pos, fee):
    p = pos.shift(1).fillna(0); r = df.c.pct_change().fillna(0)
    return p * r - p * df.f - p.diff().abs().fillna(0) * fee
print("2021-11 – 2026-11 CAGR % (2020–21 skliausteliuose), BTC+ETH, 0,05 %:")
ths = [0.0, 0.00005, 0.0001, 0.00015, 0.0002, 0.00025, 0.0003, 0.00035]
print("N \\ slenkstis %/d.: " + " ".join(f"{t*100:.3f}" for t in ths))
for N in [1, 2, 3, 5, 7, 10, 14, 21]:
    cells = []
    for th in ths:
        R = pd.concat([ret2(d, (d.f.rolling(N).mean() < th).astype(float), 0.0005) for d in data.values()], axis=1).fillna(0).mean(axis=1)
        e = (1 + R["2021-11-08":]).cumprod(); e0 = (1 + R["2020-01-01":"2021-11-08"]).cumprod()
        cells.append(f"{(e.iloc[-1]**(365.25/len(e))-1)*100:+5.0f}({(e0.iloc[-1]**(365.25/len(e0))-1)*100:+4.0f})")
    print(f"N={N:2d}: " + " ".join(cells), flush=True)
print("\nAtskirai, N=3, slenkstis 0,01 %/d.:")
for s, d in data.items():
    for fee in [0.0005, 0.001]:
        pos = (d.f.rolling(3).mean() < 0.0001).astype(float); R = ret2(d, pos, fee)
        print(f"{s} mokestis {fee*100:.2f}%: 2020–21 {st(R, '2020-01-01', '2021-11-08')} | 2021–26 {st(R, '2021-11-08', '2026-11-14')} | laiko dalis rinkoje 2021–26 {pos['2021-11-08':].mean():.0%}, įėjimų {int((pos.diff()==1)['2021-11-08':].sum())}")
