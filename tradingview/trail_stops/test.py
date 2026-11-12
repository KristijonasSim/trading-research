"""Instagram technicaltrading.tv: 8 trailing stop būdai NQ. Ar kuris nors pagerina rezultatą?
Įėjimai: (A) atsitiktiniai (3 per dieną, atsitiktinė kryptis), (B) Noise Breakout (mūsų geriausias NAS100 įrankis).
Visiems: pradinis stop 2 ATR, uždaryti iki 15:55. NAS100 5 min., RTH, 2019-2026."""
import sys
from pathlib import Path
import numpy as np, pandas as pd

D = Path(__file__).resolve().parents[1] / "ovn_box/data"
FEE = 0.0001  # viso už sandorį
df = pd.concat(pd.read_csv(f, index_col=0, parse_dates=True) for f in sorted(D.glob("NAS100_*.csv")))
df = df[~df.index.duplicated()].sort_index(); df.index = df.index.tz_convert("America/New_York")
tod = df.index.hour * 60 + df.index.minute
df = df[(tod >= 570) & (tod < 960)].copy()
df["tod"] = df.index.hour * 60 + df.index.minute; df["day"] = df.index.date
pc = df.close.shift()
tr = np.maximum(df.high - df.low, np.maximum((df.high - pc).abs(), (df.low - pc).abs()))
ATR = tr.rolling(14).mean().values
O, H, L, C = (df[k].values for k in ("open", "high", "low", "close"))
TOD = df.tod.values
days = pd.Series(np.arange(len(df))).groupby(df.day.values).agg(["first", "last"])


def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().values


def trade(j, end, sgn, method):
    """Įėjimas bar j uždarymu, kryptis sgn. Grąžina grąžą."""
    s = slice(j, end + 1)
    o, h, l, c = O[s] * sgn, H[s] * sgn, L[s] * sgn, C[s] * sgn
    if sgn < 0: h, l = l, h
    a = ATR[j]; e = c[0]; R = 2 * a; stop = e - R
    e20 = ema(c, 20) if method == "ema20" else None
    hh, sar, af, ep = h[0], l[0], 0.02, h[0]
    for k in range(1, len(c)):
        if l[k] <= stop:
            x = min(stop, o[k]); break
        if method == "ema20" and k >= 3 and c[k] < e20[k]:
            x = c[k]; break
        if k == len(c) - 1:
            x = c[k]; break
        hh = max(hh, h[k])
        if method == "fixed": stop = max(stop, hh - 0.0025 * abs(e))
        elif method == "chandelier": stop = max(stop, hh - 3 * a)
        elif method == "supertrend": stop = max(stop, (h[k] + l[k]) / 2 - 3 * a)
        elif method == "psar":
            sar = sar + af * (ep - sar)
            if h[k] > ep: ep, af = h[k], min(af + 0.02, 0.2)
            stop = max(stop, min(sar, l[k], l[k - 1]))
        elif method == "candle_low": stop = max(stop, l[k])
        elif method == "swing_low" and k >= 4 and l[k - 2] == min(l[k - 4:k + 1]): stop = max(stop, l[k - 2])
        elif method == "steps":
            if hh >= e + 2 * R: stop = max(stop, e + R)
            elif hh >= e + R: stop = max(stop, e)
    return x / e - 1 - FEE


METHODS = ["none", "fixed", "chandelier", "supertrend", "ema20", "psar", "swing_low", "candle_low", "steps"]

# (A) atsitiktiniai įėjimai
rng = np.random.default_rng(7); ents_A = []
for d, (f, l_) in days.iterrows():
    if l_ - f < 70: continue
    cand = [i for i in range(f, l_) if 600 <= TOD[i] <= 840 and not np.isnan(ATR[i])]
    for i in rng.choice(cand, 3, replace=False): ents_A.append((d, i, l_, rng.choice([1, -1])))

# (B) Noise Breakout įėjimai (kaip noise3.py: kas 60 min., 14 d. triukšmo vidurkis, VWAP)
ents_B, orig_B, hist, prev = [], [], [], None
for d, (f, l_) in days.iterrows():
    g = df.iloc[f:l_ + 1]
    full = TOD[f] == 570
    if full and len(hist) >= 14 and prev is not None and len(g) >= 70:
        sig = pd.concat(hist[-14:], axis=1).mean(axis=1).reindex(g.tod.values).values
        tp = (g.high + g.low + g.close) / 3; v = g.volume.replace(0, np.nan).fillna(1)
        vw = ((tp * v).cumsum() / v.cumsum()).values
        U0, L0 = max(g.open.iloc[0], prev), min(g.open.iloc[0], prev); pos = 0
        for jj in range(len(g)):
            t = TOD[f + jj] + 5; last = jj == len(g) - 1
            if not (((t - 570) % 60 == 0 and t >= 600) or last) or np.isnan(sig[jj]): continue
            c, U, Lb = C[f + jj], U0 * (1 + sig[jj]), L0 * (1 - sig[jj])
            if pos == 1 and (c < max(U, vw[jj]) or last): orig_B.append((d, c / e - 1 - FEE)); pos = 0
            elif pos == -1 and (c > min(Lb, vw[jj]) or last): orig_B.append((d, -(c / e - 1) - FEE)); pos = 0
            if pos == 0 and not last and not np.isnan(ATR[f + jj]):
                if c > U: pos, e = 1, c; ents_B.append((d, f + jj, l_, 1))
                elif c < Lb: pos, e = -1, c; ents_B.append((d, f + jj, l_, -1))
    if full: hist.append(pd.Series((g.close / g.open.iloc[0] - 1).abs().values, index=g.tod.values))
    prev = g.close.iloc[-1]


def summarize(ents, label, extra=None):
    rows = {}
    for m in METHODS:
        r = pd.Series([trade(j, end, s, m) for d, j, end, s in ents], index=pd.to_datetime([x[0] for x in ents]))
        rows[m] = r
    if extra is not None: rows["originalus"] = extra
    out = [f"\n{label}: {len(ents)} sandorių"]
    out.append(f"{'būdas':12} {'vid. bp':>8} {'laimi %':>8} {'2019-24 bp':>11} {'2025-26 bp':>11} {'viso %':>8}")
    for m, r in rows.items():
        a, b = r[r.index < "2025-01-01"], r[r.index >= "2025-01-01"]
        out.append(f"{m:12} {1e4 * r.mean():8.2f} {100 * (r > 0).mean():8.1f} {1e4 * a.mean():11.2f} {1e4 * b.mean():11.2f} {100 * r.sum():8.1f}")
    return out


orig = pd.Series([x[1] for x in orig_B], index=pd.to_datetime([x[0] for x in orig_B]))
out = ["bp = 0,01 % per sandorį (po 0,01 % kaštų). 'none' = tik pradinis 2 ATR stop, laikyti iki uždarymo."]
out += summarize(ents_A, "A) Atsitiktiniai įėjimai")
out += summarize(ents_B, "B) Noise Breakout įėjimai", orig)
print("\n".join(out)); (Path(__file__).parent / "REZULTATAI.txt").write_text("\n".join(out))
