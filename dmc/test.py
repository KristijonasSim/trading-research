"""DMC indikatoriaus (tradingview/DMC_indikatorius.pine) logikos backtestas ant NAS100 1 min. (Dukascopy) 2016-2026.
Lygiai: užsidariusių M/W/D/4H/1H žvakių kūnų kraštai (D/W/4H skaičiuojami nuo 18:00 NY, kaip ateities sandoriai).
Signalas: kaina paliečia įsijungusį lygį iš viršaus, žvakė užsidaro virš -> BUY (atvirkščiai SELL).
SL = už kito lygio (iki maxStop ATR), kitaip už dagties; TP = artimiausias lygis >= minRR*R, kitaip 1R. Uždaryti 16:00.
python test.py <tf_min> [trend 0/1] [sess_end_hhmm] [short 0/1]"""
import sys
from pathlib import Path
import numpy as np, pandas as pd

TF = int(sys.argv[1]) if len(sys.argv) > 1 else 5
TREND = int(sys.argv[2]) if len(sys.argv) > 2 else 1
SESS_END = int(sys.argv[3]) if len(sys.argv) > 3 else 1130
SHORT = int(sys.argv[4]) if len(sys.argv) > 4 else 1
MAXPER, ARM, MERGE, MINRR, MAXSTOP, FALLRR = 6, 1.5, 0.5, 1.0, 3.0, 1.0
COST = 0.0001  # ~2 t. viso už sandorį
ROOT = Path(__file__).resolve().parents[1]
CACHE = Path(__file__).parent / "nas100_1m.parquet"

if CACHE.exists():
    m1 = pd.read_parquet(CACHE)
else:
    fs = sorted((ROOT / "tradingview/ce50/data1m").glob("NAS100_*.csv"))
    m1 = pd.concat(pd.read_csv(f, index_col=0, parse_dates=True) for f in fs)
    m1 = m1[~m1.index.duplicated()].sort_index()[["open", "high", "low", "close"]]
    m1.index = m1.index.tz_convert("America/New_York").tz_localize(None)  # NY vietinis laikas
    m1.to_parquet(CACHE)

loc = m1.index
sh = loc - pd.Timedelta(hours=18)  # prekybos diena prasideda 18:00 NY
keys = {
    5: pd.Series(sh.year * 100 + sh.month, index=loc),
    4: pd.Series((sh - pd.to_timedelta(sh.weekday, unit="D")).normalize().asi8, index=loc),
    3: pd.Series(sh.normalize().asi8, index=loc),
    2: pd.Series(sh.normalize().asi8 + (sh.hour // 4), index=loc),
    1: pd.Series(loc.floor("h").asi8, index=loc),
}
# kiekvienos HTF žvakės kūnas ir pabaigos laikas
htf = []
for k, key in keys.items():
    g = m1.groupby(key.values)
    agg = pd.DataFrame({"o": g.open.first(), "c": g.close.last(), "end": g.apply(lambda x: x.index[-1]) + pd.Timedelta(minutes=1)})
    agg["k"] = k
    htf.append(agg)
htf = pd.concat(htf).sort_values(["end", "k"], ascending=[True, False])

bars = m1.resample(f"{TF}min", label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
O, H, L, C = (bars[c].values for c in ("open", "high", "low", "close"))
T = bars.index
pc = np.r_[np.nan, C[:-1]]
tr = np.nanmax(np.vstack([H - L, np.abs(H - pc), np.abs(L - pc)]), axis=0)
atr = pd.Series(tr).ewm(alpha=1 / 50, adjust=False).mean().values  # RMA kaip ta.atr
# HTF žvakė tampa žinoma pirmoje grafiko žvakėje, prasidedančioje >= jos pabaigos
pos = np.searchsorted(T.values, htf.end.values)
events = {}
for p_, (o, c, k) in zip(pos, htf[["o", "c", "k"]].values):
    if p_ < len(T): events.setdefault(p_, []).append((max(o, c), min(o, c), int(k)))
# 4H krypties žvakė (paskutinė užsidariusi)
h4 = htf[htf.k == 2]
h4pos = np.searchsorted(T.values, h4.end.values)
trend = np.zeros(len(T)); last = 0.0
h4dir = dict(zip(h4pos, np.sign(h4.c.values - h4.o.values)))
mins = T.hour * 60 + T.minute
close_min = mins + TF
s_end = SESS_END // 100 * 60 + SESS_END % 100

lp, lk, la = [], [], []  # lygiai


def add(p, k, a):
    for i in range(len(lp) - 1, -1, -1):
        if abs(lp[i] - p) < MERGE * a:
            if lk[i] >= k: return
            del lp[i], lk[i], la[i]
    same = [i for i in range(len(lp)) if lk[i] == k]
    if len(same) >= MAXPER: i = same[0]; del lp[i], lk[i], la[i]
    lp.append(p); lk.append(k); la.append(False)


def nearest(frm, d, mind):
    best = None
    for p in lp:
        dd = (p - frm) * d
        if dd >= mind and (best is None or dd < (best - frm) * d): best = p
    return best


trades = []; tdir = 0
for i in range(1, len(T)):
    a = atr[i]
    if i in h4dir: last = h4dir[i]
    for top, bot, k in events.get(i, []):
        if not np.isnan(a): add(top, k, a); add(bot, k, a)
    # sandorio valdymas
    if tdir != 0:
        if (tdir > 0 and L[i] <= sl) or (tdir < 0 and H[i] >= sl):
            ex = sl if (tdir > 0 and O[i] > sl) or (tdir < 0 and O[i] < sl) else O[i]
            trades.append((T[ei], tdir, e, sl0, tp, ex, "SL")); tdir = 0
        elif (tdir > 0 and H[i] >= tp) or (tdir < 0 and L[i] <= tp):
            trades.append((T[ei], tdir, e, sl0, tp, tp, "TP")); tdir = 0
        elif close_min[i] >= 960 or T[i].date() != T[ei].date():
            trades.append((T[ei], tdir, e, sl0, tp, C[i], "16:00")); tdir = 0
    # palietimai
    buyK = sellK = 0; buyP = sellP = None; done = []
    for j in range(len(lp)):
        p = lp[j]
        if la[j]:
            if pc[i] > p and L[i] <= p:
                if C[i] > p and lk[j] > buyK: buyK, buyP = lk[j], p
                done.append(j)
            elif pc[i] < p and H[i] >= p:
                if C[i] < p and lk[j] > sellK: sellK, sellP = lk[j], p
                done.append(j)
        elif abs(C[i] - p) > ARM * a:
            la[j] = True
    for j in reversed(done): del lp[j], lk[j], la[j]
    # signalai
    if tdir == 0 and 570 <= mins[i] < s_end and close_min[i] < 960:
        if buyP is not None and (not TREND or last > 0):
            e = C[i]; b = nearest(buyP, -1, 0.1 * a)
            sl = b - 0.1 * a if b is not None and e - b <= MAXSTOP * a else L[i] - 0.25 * a
            r = e - sl
            if r > 0:
                t = nearest(e, 1, MINRR * r); tp = t if t is not None else e + FALLRR * r
                tdir, ei, sl0 = 1, i, sl
        if tdir == 0 and SHORT and sellP is not None and (not TREND or last < 0):
            e = C[i]; b = nearest(sellP, 1, 0.1 * a)
            sl = b + 0.1 * a if b is not None and b - e <= MAXSTOP * a else H[i] + 0.25 * a
            r = sl - e
            if r > 0:
                t = nearest(e, -1, MINRR * r); tp = t if t is not None else e - FALLRR * r
                tdir, ei, sl0 = -1, i, sl

t = pd.DataFrame(trades, columns=["t", "dir", "e", "sl", "tp", "ex", "why"]).set_index("t")
t["R"] = (t.dir * (t.ex - t.e) - COST * t.e) / (t.dir * (t.e - t.sl))
t["y"] = t.index.year
t.to_csv(Path(__file__).parent / f"trades_{TF}m_tr{TREND}_s{SESS_END}_sh{SHORT}.csv")


def grow(r, f=0.01):
    eq = (1 + f * r).cumprod(); y = (r.index[-1] - r.index[0]).days / 365.25
    return 100 * (eq.iloc[-1] ** (1 / y) - 1), 100 * (1 - eq / eq.cummax()).max()


g, dd = grow(t.R)
out = [f"DMC {TF} min., kryptis {'4H' if TREND else 'be filtro'}, sesija 9:30-{SESS_END // 100}:{SESS_END % 100:02d}, short {'taip' if SHORT else 'ne'}",
       f"Sandorių {len(t)} ({len(t) / ((t.index[-1] - t.index[0]).days / 365.25):.0f}/m.), laimi {100 * (t.R > 0).mean():.0f} %, vid. {t.R.mean():+.3f} R, "
       f"TP {100 * (t.why == 'TP').mean():.0f} % / SL {100 * (t.why == 'SL').mean():.0f} % / 16:00 {100 * (t.why == '16:00').mean():.0f} %",
       f"1 % rizika: {g:+.1f} %/m., kritimas {dd:.0f} %",
       "Metai (vid. R): " + ", ".join(f"{y} {v:+.2f}" for y, v in t.groupby("y").R.mean().items()),
       f"BUY {t[t.dir > 0].R.mean():+.3f} R ({(t.dir > 0).sum()}), SELL {t[t.dir < 0].R.mean():+.3f} R ({(t.dir < 0).sum()})"]
print("\n".join(out))
with open(Path(__file__).parent / "REZULTATAI.txt", "a") as f: f.write("\n".join(out) + "\n\n")
