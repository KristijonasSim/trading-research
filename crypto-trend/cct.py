"""Catching Crypto Trends (Zarattini, Pagani, Barbon 2025, SSRN 5209907) – kopija pagal straipsnį, Binance dienos duomenys.

Kiekvienai monetai ir kiekvienam Donchian ilgiui n ∈ {5,10,20,30,60,90,150,250,360}:
  long, kai close = n dienų maksimumas (įskaitant šiandieną); stop = max(vakar stop, n d. vidurio linija);
  išeina, kai close <= stop. Svoris w_n = min(VT/σ90, CAP) (σ – 90 d. metinis svyravimas, 365 d.).
  Combo = vidurkis per n. Perbalansuojama iškart po signalo, o dėl svyravimo – tik jei |tikslas−dabar| > 20 % tikslo.
Portfelis: mėnesio pabaigoje 20 monetų pagal 30 d. medianinę apyvartą (≥ 2 mln. $, ≥ 365 d. biržoje, be stablecoin'ų,
  wrapped ir sverto žetonų); kiekviena gauna 1/20 kapitalo; išmetama vidury mėnesio, jei apyvarta < 1 mln. $
  arba medianinis dienos pokytis < 0,5 %. Mokestis 0,1 % nuo apyvartos.
Naudojimas: python cct.py <binance_daily dir>
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

NS = [5, 10, 20, 30, 60, 90, 150, 250, 360]
STABLE = {"USDC", "BUSD", "TUSD", "USDP", "PAX", "DAI", "FDUSD", "USDE", "UST", "USTC", "SUSD", "EUR", "GBP", "AUD",
          "PAXG", "WBTC", "WBETH", "BETH", "BKRW", "BIDR", "IDRT", "AEUR", "EURI", "USD1", "XUSD", "BFUSD", "RLUSD", "USDS"}


def load(d):
    C, V = {}, {}
    for f in sorted(Path(d).glob("*USDT.csv")):
        b = f.stem[:-4]
        if b in STABLE or b.endswith(("UP", "DOWN", "BULL", "BEAR")) and len(b) > 4:
            continue
        x = pd.read_csv(f, parse_dates=["date"]).set_index("date")
        if len(x) < 400:
            continue
        C[b], V[b] = x.close, x.qvol
    return pd.DataFrame(C).sort_index(), pd.DataFrame(V).sort_index()


def coin_weights(c, vt, cap, long_short=False):
    """Tikslinis Combo svoris (dienos pabaigoje) ir signalo pasikeitimo žymė vienai monetai."""
    c = c.dropna()
    ret = c.pct_change()
    sig = ret.rolling(90).std() * np.sqrt(365)
    size = (vt / sig).clip(upper=cap)
    W = np.zeros(len(c)); chg = np.zeros(len(c), bool)
    cv = c.values
    for n in NS:
        up = c.rolling(n).max().values; dn = c.rolling(n).min().values; mid = 0.5 * (up + dn)
        pos, stop = 0, np.nan
        P = np.zeros(len(c))
        for t in range(len(c)):
            if np.isnan(up[t]):
                continue
            prev = pos
            if pos == 1 and cv[t] <= stop:
                pos = 0
            elif pos == -1 and cv[t] >= stop:
                pos = 0
            if pos == 0:
                if cv[t] >= up[t]:
                    pos, stop = 1, mid[t]
                elif long_short and cv[t] <= dn[t]:
                    pos, stop = -1, mid[t]
            if pos == 1:
                stop = max(stop, mid[t])
            elif pos == -1:
                stop = min(stop, mid[t])
            P[t] = pos
            chg[t] |= pos != prev
        W += P
    W = W / len(NS) * size.fillna(0).values
    return pd.Series(W, c.index), pd.Series(chg, c.index)


def backtest(C, V, vt=0.25, cap=2.0, B=20, fee=0.001, thr=0.2, long_short=False, start="2018-09-01"):
    R = C.pct_change()
    first = C.apply(lambda s: s.first_valid_index())
    last = C.apply(lambda s: s.last_valid_index())
    tw, tc = {}, {}
    for b in C:
        w, ch = coin_weights(C[b], vt, cap, long_short)
        tw[b], tc[b] = w, ch
    TW = pd.DataFrame(tw).reindex(C.index).fillna(0)
    TC = pd.DataFrame(tc).reindex(C.index).fillna(False)
    medv = V.rolling(30).median()
    medchg = R.abs().rolling(30).median()
    days = C.loc[start:].index
    months = pd.Series(days.to_period("M"), days)
    uni, held, sleeve, cash = [], {}, {}, 1.0
    out = []
    for i, d in enumerate(days):
        for b in uni:  # dienos grąža pagal vakar svorius
            r = R.at[d, b]
            sleeve[b] *= 1 + held[b] * (0.0 if np.isnan(r) else r)
        for b in uni:  # svoriai dienos pabaigoje
            alive = d <= last[b] and medv.at[d, b] >= 1e6 and medchg.at[d, b] >= 0.005
            tgt = TW.at[d, b] if alive else 0.0
            cur = held[b]
            if tgt != cur and (TC.at[d, b] or not alive or tgt == 0 or cur == 0 or abs(tgt - cur) > thr * abs(cur)):
                sleeve[b] -= abs(tgt - cur) * fee * sleeve[b]
                held[b] = tgt
        total = sum(sleeve.values()) + cash
        if i == len(days) - 1 or months.iloc[i + 1] != months.iloc[i]:  # mėnesio pabaiga
            elig = [b for b in C if not np.isnan(C.at[d, b]) and (d - first[b]).days >= 365 and medv.at[d, b] >= 2e6]
            new = sorted(elig, key=lambda b: -medv.at[d, b])[:B]
            for b in uni:
                if b not in new:
                    total -= abs(held[b]) * fee * sleeve[b]
            nh = {}
            for b in new:
                if b in uni:
                    nh[b] = held[b]
                else:
                    nh[b] = TW.at[d, b]
                    total -= abs(nh[b]) * fee * total / B
            uni, held = new, nh
            sleeve = {b: total / B for b in uni}
            cash = total * (B - len(uni)) / B
        out.append((d, total))
    return pd.Series(dict(out))


def st(eq, a, b):
    e = eq[a:b]
    if len(e) < 30:
        return "-"
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    return f"{100*((e.iloc[-1]/e.iloc[0])**(1/yrs)-1):5.1f}%/m kritimas {100*(1-e/e.cummax()).max():3.0f}%"


if __name__ == "__main__":
    C, V = load(sys.argv[1])
    print("monetų:", C.shape[1], "nuo", C.index[0].date())
    btc = C["BTC"]
    P = [("2018-09-01", "2021-11-08"), ("2021-11-08", "2026-11-08"), ("2025-04-01", "2026-11-08"), ("2018-09-01", "2026-11-08")]
    print(" " * 34 + " | ".join(f"{a[:7]}..{b[:7]}".ljust(22) for a, b in P))
    print(f"{'laikyti BTC':34}" + " | ".join(st(btc, a, b).ljust(22) for a, b in P))
    for lab, kw in [("straipsnis (VT 25%, cap 200%)", {}), ("spot be sverto (cap 100%)", dict(cap=1.0)),
                    ("VT 50%, cap 200%", dict(vt=0.5)), ("long+short (VT 25%)", dict(long_short=True))]:
        eq = backtest(C, V, **kw)
        eq.to_csv(f"eq_{lab.split()[0]}_{kw.get('vt', .25)}_{kw.get('cap', 2)}_{int(kw.get('long_short', 0))}.csv")
        print(f"{lab:34}" + " | ".join(st(eq, a, b).ljust(22) for a, b in P))
        yr = eq.groupby(eq.index.year).apply(lambda e: round(100 * (e.iloc[-1] / e.iloc[0] - 1)))
        print(" " * 34 + str(yr.to_dict()))
