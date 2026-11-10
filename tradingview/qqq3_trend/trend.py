"""3x Nasdaq (QQQ3/TQQQ) tik kai QQQ virš 200 d. vidurkio. Sintetinis 3x nuo 1999 m. (3x dienos grąža − finansavimas − 0,95 %/m.).
Signalas dienos uždarymu, pozicija nuo kitos dienos; 0,1 % mokestis už kiekvieną perjungimą; išėjus – palūkanos (T-bills).
Juosta b: įeina kai close > SMA×(1+b), išeina kai close < SMA×(1−b) (mažiau „pjūklo“)."""
import sys, numpy as np, pandas as pd
d = pd.read_pickle(sys.argv[1])["Close"]
q = d["QQQ"].dropna(); rate = (d["^IRX"].reindex(q.index).ffill() / 100).fillna(0.02)
qr = q.pct_change().fillna(0)
cash = rate / 252
lev = 3 * qr - 2 * cash - 0.0095 / 252
real = d["TQQQ"].dropna().pct_change()
both = pd.concat([lev, real], axis=1).dropna()
print("sintetinis vs tikras TQQQ 2010-2026: koreliacija %.4f, CAGR %.1f%% vs %.1f%%" % (both.corr().iloc[0, 1],
      100 * ((1 + both.iloc[:, 0]).prod() ** (252 / len(both)) - 1), 100 * ((1 + both.iloc[:, 1]).prod() ** (252 / len(both)) - 1)))
def run(n=200, b=0.0, asset=lev):
    sma = q.rolling(n).mean()
    pos = pd.Series(np.nan, q.index)
    pos[q > sma * (1 + b)] = 1; pos[q < sma * (1 - b)] = 0
    pos = pos.ffill().fillna(0)
    p = pos.shift(1).fillna(0)
    r = p * asset + (1 - p) * cash - pos.diff().abs().shift(1).fillna(0) * 0.001
    return r, pos
def st(r, a, b):
    r = r[a:b]; eq = (1 + r).cumprod(); y = len(r) / 252
    return f"{100*(eq.iloc[-1]**(1/y)-1):5.1f}%/m kritimas {100*(1-eq/eq.cummax()).max():4.0f}%"
P = [("2000-01-01", "2010-12-31"), ("2011-01-01", "2020-12-31"), ("2021-01-01", "2026-11-10"), ("2000-01-01", "2026-11-10")]
print("%-26s" % "", " | ".join(f"{a[:4]}-{b[:4]}" .ljust(24) for a, b in P))
rows = [("laikyti QQQ", qr), ("laikyti 3x", lev), ("QQQ >200d (1x)", run(asset=qr)[0])]
for b in (0, 0.01, 0.02, 0.03, 0.05):
    r, pos = run(b=b); rows.append((f"3x >200d juosta {b*100:.0f}%  ({int(pos.diff().abs().sum()/26.7)}/m)", r))
for n in (150, 250):
    rows.append((f"3x >{n}d juosta 3%", run(n, 0.03)[0]))
for lab, r in rows:
    print("%-26s" % lab, " | ".join(st(r, a, b).ljust(24) for a, b in P))
r, pos = run(b=0.03)
yr = r.groupby(r.index.year).apply(lambda x: round(100 * ((1 + x).prod() - 1)))
print("3x juosta 3% pagal metus:", yr.to_dict())
