"""Instagram silk.mechanics: „efektyvi riba“ (Markowitz). Ar portfelis, parinktas pagal praeitį, ir ateityje duoda daugiau grąžos už riziką?
12 ETF (akcijos, obligacijos, auksas, žaliavos, NT), kas mėnesį perskaičiuojama pagal paskutinius 3 m., 2009-2026."""
from pathlib import Path
import numpy as np, pandas as pd
from scipy.optimize import minimize

P = pd.read_csv(Path(__file__).parent / "prices.csv", index_col=0, parse_dates=True).dropna()
R = P.pct_change().dropna()
ME = R.resample("ME").last().index
N = R.shape[1]; COST = 0.0005  # 0,05 % nuo apyvartos


def opt(mu, cov, kind):
    w0 = np.ones(N) / N; b = [(0, 1)] * N; con = [{"type": "eq", "fun": lambda w: w.sum() - 1}]
    if kind == "minvar": f = lambda w: w @ cov @ w
    elif kind == "maxsharpe": f = lambda w: -(w @ mu) / np.sqrt(w @ cov @ w)
    elif kind == "sametrisk":  # tiek pat rizikos kaip 1/N, bet daugiausia grąžos (taškas ant ribos)
        tv = w0 @ cov @ w0; f = lambda w: -(w @ mu)
        con = con + [{"type": "ineq", "fun": lambda w: tv - w @ cov @ w}]
    return minimize(f, w0, bounds=b, constraints=con, method="SLSQP").x


methods = ["maxsharpe", "minvar", "sametrisk"]
W = {m: {} for m in methods}; pred = []
for d in ME[ME >= "2009-01-01"]:
    h = R[(R.index <= d) & (R.index > d - pd.DateOffset(years=3))]
    mu, cov = h.mean().values * 252, h.cov().values * 252
    for m in methods: W[m][d] = opt(mu, cov, m)
    w = W["maxsharpe"][d]; pred.append((d, (w @ mu) / np.sqrt(w @ cov @ w)))
fixed = {"1/N": np.ones(N) / N,
         "60/40": np.array([0.6 if c == "SPY" else 0.4 if c == "IEF" else 0 for c in R.columns]),
         "SPY": np.array([1.0 if c == "SPY" else 0 for c in R.columns])}


def backtest(wmap):
    start = min(wmap) if isinstance(wmap, dict) else ME[ME >= "2009-01-01"][0]
    rets, w_prev = [], np.zeros(N)
    for d in ME[(ME >= start)][:-1]:
        w = wmap[d] if isinstance(wmap, dict) else wmap
        nxt = ME[ME > d][0]; r = R[(R.index > d) & (R.index <= nxt)]
        grow = (1 + r).cumprod().values @ w
        daily = np.diff(np.concatenate([[1], grow]))
        daily = daily / np.concatenate([[1], grow[:-1]])
        daily[0] -= COST * np.abs(w - w_prev).sum(); w_prev = w
        rets.append(pd.Series(daily, index=r.index))
    return pd.concat(rets)


def stats(r):
    eq = (1 + r).cumprod(); y = len(r) / 252
    cagr = eq.iloc[-1] ** (1 / y) - 1; vol = r.std() * np.sqrt(252)
    return dict(cagr=100 * cagr, vol=100 * vol, ret_per_risk=cagr / vol, dd=100 * (1 - eq / eq.cummax()).max())


out = ["Portfelis       grąža %/m  svyravimai %  grąža/rizika  max kritimas %   (2009-01..2026-11)"]
res = {}
for name, wm in [("maks. Sharpe", W["maxsharpe"]), ("min. rizika", W["minvar"]), ("riba @1/N rizika", W["sametrisk"])] + list(fixed.items()):
    r = backtest(wm); res[name] = r; s = stats(r)
    out.append(f"{name:16} {s['cagr']:9.1f} {s['vol']:13.1f} {s['ret_per_risk']:13.2f} {s['dd']:15.1f}")
p = pd.Series(dict(pred)); real = res["maks. Sharpe"]
out.append(f"\nMaks. Sharpe: žadėta (pagal praeitį) grąža/rizika vid. {p.mean():.2f}, realiai gauta {stats(real)['ret_per_risk']:.2f}")
out.append("\nPagal 3 laikotarpius (grąža/rizika):")
for a, b in [("2009", "2014"), ("2015", "2020"), ("2021", "2026")]:
    out.append(f"  {a}-{b}: " + ", ".join(f"{k} {stats(v[a:b])['ret_per_risk']:.2f}" for k, v in res.items()))
wm = pd.DataFrame(W["maxsharpe"], index=R.columns).T
out.append(f"\nMaks. Sharpe vid. apyvarta per mėn.: {100 * wm.diff().abs().sum(axis=1).mean() / 2:.0f} %, vid. svoriai: "
           + ", ".join(f"{c} {100 * v:.0f}%" for c, v in wm.mean().sort_values(ascending=False).head(5).items()))
print("\n".join(out)); (Path(__file__).parent / "REZULTATAI.txt").write_text("\n".join(out))
