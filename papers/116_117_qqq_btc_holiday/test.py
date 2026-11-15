"""116: kas savaitę laikyti tą iš QQQ/BTC, kurio N d. grąža didesnė (jei abi < 0 – grynieji). Mokestis 0,1 % keitimui.
117: BTC laikyti 1–3 d. prieš JAV federalines šventes (likusį laiką grynieji); lyginama su atsitiktinėmis dienomis."""
import os, numpy as np, pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar
R0 = os.path.expanduser("~/Desktop/trading-research")
q = pd.read_csv(f"{R0}/quantconnect-lean/raw/daily/QQQ.csv", parse_dates=["Date"]).set_index("Date").Close
b = pd.read_csv(f"{R0}/papers/data/binance_1d/BTCUSDT.csv"); b = pd.Series(b.c.values, pd.to_datetime(b.t, unit="ms"))
FEE = 0.001
def st(r, a, z):
    r = r[(r.index >= a) & (r.index < z)]; e = (1 + r).cumprod(); y = (r.index[-1] - r.index[0]).days / 365.25
    return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+.1f} | {(e / e.cummax() - 1).min() * 100:.0f} %"
P = ["2019-01-01", "2021-11-08", "2026-11-08"]
out = ["# 116/117 – rezultatai\n", "| Variantas | 2019–21 %/m. / kritimas | 2021–26 %/m. / kritimas |", "|---|---|---|"]
# 116: dienos kalendorius = BTC (7 d.), QQQ ffill
df = pd.DataFrame({"q": q, "b": b}).sort_index().ffill().dropna(); R = df.pct_change().fillna(0)
for name, r in [("BTC laikyti", R.b), ("QQQ laikyti", R.q), ("50/50 kas sav.", (R.b + R.q) / 2)]:
    out.append(f"| {name} | {st(r, P[0], P[1])} | {st(r, P[1], P[2])} |")
for N in (28, 56, 90, 180):
    for cash in (True, False):
        m = df.pct_change(N); pos = pd.Series(np.where(m.b > m.q, "b", "q"), df.index)
        if cash: pos[(m.b < 0) & (m.q < 0)] = "c"
        pos[m.isna().any(axis=1)] = "c"
        pos = pos.where(df.index.dayofweek == 0).ffill().fillna("c").shift(1).fillna("c")
        r = pd.Series(np.select([pos == "b", pos == "q"], [R.b, R.q], 0.0), df.index) - (pos != pos.shift()).astype(float) * FEE
        out.append(f"| 116 rotacija {N} d.{', grynieji jei abu < 0' if cash else ''} | {st(r, P[0], P[1])} | {st(r, P[1], P[2])} |")
# 117
rb = b.pct_change().fillna(0); hol = USFederalHolidayCalendar().holidays("2017-01-01", "2027-01-01")
for k in (1, 2, 3):
    inpos = pd.Series(False, rb.index)
    for h in hol:
        for j in range(1, k + 1): d = h - pd.Timedelta(days=j - 1)
        idx = [h - pd.Timedelta(days=j) for j in range(0, k)]  # grąžos dienos h-k+1..h (t.y. laikoma k d. iki šventės pabaigos)
        inpos[inpos.index.isin(idx)] = True
    r = rb.where(inpos, 0) - inpos.astype(int).diff().abs().fillna(0) * FEE / 2
    for a, z in [("2018-01-01", "2021-11-08"), ("2021-11-08", "2026-11-08")]:
        x = rb[(rb.index >= a) & (rb.index < z)]; xi = inpos[x.index]
        pass
    vid = lambda a, z: (rb[(rb.index >= a) & (rb.index < z) & inpos].mean() * 100, rb[(rb.index >= a) & (rb.index < z) & ~inpos].mean() * 100)
    v1, v2 = vid("2018-01-01", "2021-11-08"), vid("2021-11-08", "2026-11-08")
    out.append(f"| 117 BTC {k} d. iki šventės (vid. diena {v1[0]:+.2f} % vs {v1[1]:+.2f} % / {v2[0]:+.2f} % vs {v2[1]:+.2f} %) | {st(r, '2018-01-01', P[1])} | {st(r, P[1], P[2])} |")
open("rezultatai_raw.md", "w").write("\n".join(out) + "\n"); print("\n".join(out))
