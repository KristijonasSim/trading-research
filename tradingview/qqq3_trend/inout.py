"""In & Out (Guenther 2020, QuantConnect forumo versija b99c4d7ebb, ištaisyta) pandas'e, 2008–2026, 1x ir 3x Nasdaq.
Išėjimas (tikrinama kasdien): sidabras/auksas IR pramonė (XLI)/komunalinės (XLU) per RET dienų abu krito -> OUT (TLT/IEF 50/50).
Grįžimas: tik savaitės paskutinę dieną, kai praėjo WAIT dienų nuo paskutinio OUT signalo.
WAIT = int(vol*80), RET = int((1-vol)*80), vol = QQQ 126 d. metinis svyravimas.
Signalas vakar uždarymo kainomis, sandoris šiandien uždarymu; 0,1 % mokestis; 3x = 3x dienos grąža - finansavimas - 0,95 %/m."""
import sys, numpy as np, pandas as pd
d = pd.read_pickle(sys.argv[1])["Close"].dropna(subset=["QQQ"])
C = d[["QQQ", "SLV", "GLD", "XLI", "XLU", "TLT", "IEF"]].ffill()
rate = (d["^IRX"].ffill() / 100).fillna(0.02) / 252
R = C.pct_change().fillna(0)
lev3 = 3 * R.QQQ - 2 * rate - 0.0095 / 252
out_r = 0.5 * R.TLT + 0.5 * R.IEF
vol = R.QQQ.rolling(126).std() * np.sqrt(252)
idx = C.index
week_end = pd.Series(idx.to_period("W").astype(str), idx)
week_end = week_end != week_end.shift(-1)

state = np.ones(len(idx))  # 1 = in, 0 = out (pozicija šiandienos uždarymui)
be_in, dcount, outday = True, 0, -10 ** 9
for i in range(130, len(idx)):
    v = vol.iloc[i - 1]
    wait, ret = int(v * 80), int((1 - v) * 80)
    h = C.iloc[i - ret - 2:i]  # iki vakar
    ab = (h.SLV.iloc[-1] / h.SLV.iloc[0]) / (h.GLD.iloc[-1] / h.GLD.iloc[0])
    cd = (h.XLI.iloc[-1] / h.XLI.iloc[0]) / (h.XLU.iloc[-1] / h.XLU.iloc[0])
    if ab < 1 and cd < 1:
        be_in, outday = False, dcount
    elif dcount >= outday + wait:
        be_in = True
    dcount += 1
    prev = state[i - 1]
    if not be_in:
        state[i] = 0
    elif prev == 0 and not week_end.iloc[i]:
        state[i] = 0  # grįžta tik savaitės pabaigoje
    else:
        state[i] = 1
pos = pd.Series(state, idx)
p = pos.shift(1).fillna(1)  # pozicija nuo vakar uždarymo
sw = pos.diff().abs().shift(1).fillna(0) * 0.001 * 2


def st(r, a, b):
    r = r[a:b]; eq = (1 + r).cumprod(); y = len(r) / 252
    return f"{100*(eq.iloc[-1]**(1/y)-1):5.1f}%/m kritimas {100*(1-eq/eq.cummax()).max():3.0f}%"


P = [("2008-01-01", "2014-12-31"), ("2015-01-01", "2020-12-31"), ("2021-11-08", "2026-11-08"), ("2008-01-01", "2026-11-08")]
rows = [("laikyti QQQ", R.QQQ), ("In&Out QQQ (1x)", p * R.QQQ + (1 - p) * out_r - sw),
        ("In&Out QQQ, out = grynieji", p * R.QQQ + (1 - p) * rate - sw),
        ("laikyti 3x", lev3), ("In&Out 3x (QQQ3)", p * lev3 + (1 - p) * out_r - sw),
        ("In&Out 3x, out = grynieji", p * lev3 + (1 - p) * rate - sw)]
print(" " * 28 + " | ".join(f"{a[:4]}-{b[:4]}".ljust(22) for a, b in P))
for lab, r in rows:
    print(f"{lab:28}" + " | ".join(st(r, a, b).ljust(22) for a, b in P))
print("laiko rinkoje: %.0f%%, perjungimų per metus: %.1f" % (100 * pos["2008":].mean(), pos["2008":].diff().abs().sum() / 18.8))
r3 = p * lev3 + (1 - p) * out_r - sw
print("3x pagal metus:", r3["2008":].groupby(r3["2008":].index.year).apply(lambda x: round(100 * ((1 + x).prod() - 1))).to_dict())
r1 = p * R.QQQ + (1 - p) * out_r - sw
print("1x pagal metus:", r1["2008":].groupby(r1["2008":].index.year).apply(lambda x: round(100 * ((1 + x).prod() - 1))).to_dict())
