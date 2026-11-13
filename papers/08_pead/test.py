#!/usr/bin/env python3
"""#8 Pelno anonsų dreifas (PEAD; Ball, Brown 1968; Bernard, Thomas 1989).
S&P 500 akcijos (tik tuo metu indekse), Yahoo pelno datos ir EPS staigmena (%).
Signalas žinomas reakcijos dienos rytą (anonsas po uždarymo -> kita diena; prieš atidarymą -> ta pati diena).
Įeinama reakcijos dienos UŽDARYMU (pati reakcija nepagaunama – konservatyvu) arba kitos dienos uždarymu,
laikoma H prekybos dienų. Long: staigmena tarp top 20 % per paskutines 90 d. anonsų; short: bottom 20 %.
Portfelis: lygūs svoriai tarp aktyvių pozicijų, mokestis 0,1 % už įėjimą ir išėjimą."""
import pickle, numpy as np, pandas as pd, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../07_lowvol"))
exec(open("test.py").read().split("W = {k")[0])
os.chdir("../08_pead")
E = pickle.load(open("data/earn.pkl", "rb"))
FEE = 0.001
tidx = C.index
rows = []
for t, e in E.items():
    if e is None or len(e) == 0 or t not in C.columns: continue
    e = e.dropna(subset=["Surprise(%)"])
    for ts, s in e["Surprise(%)"].items():
        ts = pd.Timestamp(ts); d = ts.tz_localize(None).normalize() if ts.tzinfo else ts.normalize()
        after = ts.hour >= 12
        i = tidx.searchsorted(d, side="right" if after else "left")
        if i >= len(tidx): continue
        rows.append((t, tidx[i], float(s)))
ev = pd.DataFrame(rows, columns=["t", "react", "s"]).drop_duplicates(["t", "react"])
# tik indekse esančios reakcijos dieną
memb = {}
def is_m(t, d):
    k = H.index.searchsorted(d, side="right") - 1
    if k < 0: return False
    if k not in memb: memb[k] = set(x.replace(".", "-") for x in H.iloc[k])
    return t in memb[k]
ev = ev[[is_m(t, d) for t, d in zip(ev.t, ev.react)]].sort_values("react").reset_index(drop=True)
ev = ev[(ev.s > -500) & (ev.s < 500)]
# kryžminis rangas tarp paskutinių 90 d. anonsų (tik praeitis + ta diena)
ev["rank"] = np.nan
v = ev.set_index("react").s
for i, (d, s) in enumerate(zip(ev.react, ev.s)):
    w = v[d - pd.Timedelta(days=90):d]
    ev.iat[i, ev.columns.get_loc("rank")] = (w < s).mean() + 0.5 * (w == s).mean() if len(w) >= 30 else np.nan
print("anonsų:", len(ev), "nuo", ev.react.min().date(), "akcijų:", ev.t.nunique())
print("anonsų per metus:", ev.groupby(ev.react.dt.year).size().to_dict())


def bt(H_=60, delay=0, q=0.2, side="long"):
    n = len(tidx); cols = {c: j for j, c in enumerate(C.columns)}
    Wl = np.zeros((n, len(cols))); Ws = np.zeros((n, len(cols)))
    for t, d, rk in zip(ev.t, ev.react, ev["rank"]):
        if np.isnan(rk): continue
        i0 = tidx.get_loc(d) + delay
        if i0 + 1 >= n: continue
        i1 = min(i0 + H_, n - 1)
        if rk >= 1 - q: Wl[i0 + 1:i1 + 1, cols[t]] = 1
        elif rk <= q: Ws[i0 + 1:i1 + 1, cols[t]] = 1
    Rv = R.fillna(0).values
    def leg(W):
        k = W.sum(1, keepdims=True); w = np.divide(W, k, out=np.zeros_like(W), where=k > 0)
        turn = np.abs(np.diff(w, axis=0, prepend=0)).sum(1)
        return (w * Rv).sum(1) - turn * FEE, (k[:, 0] > 0)
    rl, al = leg(Wl); rs_, as_ = leg(Ws)
    if side == "long": r = rl
    elif side == "short": r = -rs_
    else: r = np.where(al & as_, 0.5 * rl + 0.5 * (-rs_) , 0)
    return pd.Series(r, tidx)


def st(r, a, b):
    r = r[a:b]; r = r[r.ne(0).cumsum() > 0]
    if len(r) < 200: return ["–"] * 3
    eq = (1 + r).cumprod(); y = len(r) / 252
    return [f"{(eq.iloc[-1] ** (1 / y) - 1) * 100:+.1f}", f"{(eq / eq.cummax() - 1).min() * 100:.0f}", f"{r.mean() / r.std() * np.sqrt(252):.2f}"]


S = {}
for Hh in [20, 60]:
    for delay in [0, 1]:
        S[f"Long top 20 %, {Hh} d., įėjimas +{delay} d."] = bt(Hh, delay, 0.2, "long")
S["Long top 10 %, 60 d."] = bt(60, 0, 0.1, "long")
S["Long-short 20 %, 60 d."] = bt(60, 0, 0.2, "ls")
S["Long bottom 20 % (blogi), 60 d."] = -bt(60, 0, 0.2, "short")
ew = pd.DataFrame(0.0, C.index, C.columns)
for dt in me[:-1]:
    m = [t for t in members(dt) if t in C.columns and not np.isnan(C.at[dt, t])]
    ew.loc[dt, m] = 1 / len(m)
ew = ew.loc[me[:-1]].reindex(C.index).ffill().fillna(0).shift(1).fillna(0)
S["Visos S&P akcijos (lygiavertis)"] = (ew * R.fillna(0)).sum(1)
S["SPY"] = rs.fillna(0)
per = [("2005", "2013"), ("2014", "2026"), ("2020", "2026")]
out = "| Variantas | " + " | ".join(f"{a}–{b} %/m | kritimas | Sharpe" for a, b in per) + " |\n|" + "---|" * 10 + "\n"
for k, r in S.items():
    out += f"| {k} | " + " | ".join(" | ".join(st(r, a, b)) for a, b in per) + " |\n"
yr = pd.DataFrame({k: (1 + r["2014":]).groupby(r["2014":].index.year).prod() - 1 for k, r in S.items()}).mul(100).round(1)
out += "\nMetai (%):\n\n" + yr.T.to_markdown()
print(out); open("REZULTATAI.txt", "w").write(out + "\n")
