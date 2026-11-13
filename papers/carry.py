"""Straipsniai 3 ir 4: funding rate carry (Schmeling, Schrimpf, Todorov 2023) ir cash-and-carry.
Binance USDT-M perpetual, dienos lygiu (funding susumuojamas per dieną). Mokesčiai: futures 0,05 %, spot 0,1 %.
Kūrimo 2020–2021, nematytas 2022-01 – 2026-11. Paleisti: python papers/carry.py"""
import glob, os, json
import numpy as np, pandas as pd
D = os.path.dirname(os.path.abspath(__file__))
FF, FS = 0.0005, 0.001
from xsec import stats

def load():
    fr, px, qv, sp = {}, {}, {}, {}
    for f in glob.glob(f"{D}/data/perp_1d/*.csv"):
        s = os.path.basename(f)[:-4]; d = pd.read_csv(f)
        g = f"{D}/data/funding/{s}.csv"
        if len(d) < 60 or not os.path.exists(g): continue
        r = pd.read_csv(g)
        if len(r) < 60: continue
        i = pd.to_datetime(d.t, unit="ms"); px[s] = pd.Series(d.c.values, i); qv[s] = pd.Series(d.qv.values, i)
        fr[s] = pd.Series(r.rate.values, pd.to_datetime(r.t, unit="ms").dt.floor("D")).groupby(level=0).sum()
        h = f"{D}/data/binance_1d/{s}.csv"
        if os.path.exists(h):
            q = pd.read_csv(h); sp[s] = pd.Series(q.c.values, pd.to_datetime(q.t, unit="ms"))
    P = pd.DataFrame(px).sort_index(); P = P[P.index >= "2020-01-01"]
    return P, pd.DataFrame(qv).reindex(P.index), pd.DataFrame(fr).reindex(P.index), pd.DataFrame(sp).reindex(P.index)

def xs_carry(P, V, FR, topn=50, q=0.2, look=3, step=1, side="ls"):
    """Kas step d.: short didžiausio vid. funding 20 %, long mažiausio 20 % (side='ls'); 'short' – tik short."""
    R = P.pct_change(fill_method=None).fillna(0); FRf = FR.fillna(0)
    liq = V.rolling(30, min_periods=20).mean(); sig = FR.rolling(look, min_periods=1).mean()
    age = P.notna().cumsum()
    w = pd.Series(0.0, index=P.columns); eq = 1.0; out = []
    for i in range(40, len(P)):
        if (i - 40) % step == 0:
            ok = (age.iloc[i - 1] >= 30) & P.iloc[i - 1].notna() & liq.iloc[i - 1].notna() & sig.iloc[i - 1].notna()
            uni = liq.iloc[i - 1][ok].nlargest(topn).index
            sc = sig.iloc[i - 1][uni].sort_values(); k = max(1, int(len(sc) * q))
            nw = pd.Series(0.0, index=P.columns)
            if side == "ls": nw[sc.index[-k:]] = -0.5 / k; nw[sc.index[:k]] = 0.5 / k
            else: nw[sc.index[-k:]] = -1 / k
            eq *= 1 - (nw - w).abs().sum() * FF; w = nw
        ret = (w * R.iloc[i]).sum() - (w * FRf.iloc[i]).sum()   # short gauna funding, kai jis teigiamas
        eq *= 1 + ret; out.append((P.index[i], eq))
    return pd.Series(dict(out))

def cash_carry(P, FR, S, syms=None, k=5, look=7, thr=0.0, step=7):
    """Delta neutrali: long spot + short perp (1x, pusė kapitalo kiekvienoje kojoje) monetoms su didžiausiu
    vid. funding (tik jei > thr). Pelnas = funding + bazės pokytis − mokesčiai."""
    RP = P.pct_change(fill_method=None).fillna(0); RS = S.pct_change(fill_method=None).fillna(0); FRf = FR.fillna(0)
    sig = FR.rolling(look, min_periods=3).mean()
    cols = [c for c in (syms or P.columns) if c in S.columns]
    w = pd.Series(0.0, index=cols); eq = 1.0; out = []
    for i in range(40, len(P)):
        if (i - 40) % step == 0:
            ok = P.iloc[i - 1][cols].notna() & S.iloc[i - 1][cols].notna()
            sc = sig.iloc[i - 1][cols][ok].dropna().sort_values()
            sel = sc[sc > thr].index[-k:]
            nw = pd.Series(0.0, index=cols); nw[sel] = 0.5 / max(len(sel), 1) if len(sel) else 0
            eq *= 1 - (nw - w).abs().sum() * (FF + FS); w = nw
        ret = (w * (RS.iloc[i][cols] - RP.iloc[i][cols] + FRf.iloc[i][cols])).sum()
        eq *= 1 + ret; out.append((P.index[i], eq))
    return pd.Series(dict(out))

if __name__ == "__main__":
    P, V, FR, S = load()
    print("kontraktų:", P.shape[1], "su spot:", S.notna().any().sum(), P.index[0].date(), P.index[-1].date(), flush=True)
    T = {
        "3 Funding carry long-short, kas d.": lambda: xs_carry(P, V, FR),
        "3 Funding carry long-short, kas sav.": lambda: xs_carry(P, V, FR, step=7, look=7),
        "3 Funding carry, top 20 monetų, kas sav.": lambda: xs_carry(P, V, FR, topn=20, step=7, look=7),
        "4 Cash-and-carry BTC+ETH": lambda: cash_carry(P, FR, S, ["BTCUSDT", "ETHUSDT"], k=2, thr=-1),
        "4 Cash-and-carry BTC+ETH tik kai funding > 0": lambda: cash_carry(P, FR, S, ["BTCUSDT", "ETHUSDT"], k=2),
        "4 Cash-and-carry top 5 funding (visos)": lambda: cash_carry(P, FR, S, k=5),
        "4 Cash-and-carry top 10 funding (visos)": lambda: cash_carry(P, FR, S, k=10),
    }
    res = {}
    for n, f in T.items():
        e = f(); res[n] = {"2020-2021": stats(e, "2020-01-01", "2022-01-01"), "2022-2026": stats(e, "2022-01-01", "2027-01-01")}
        print(n, json.dumps(res[n], ensure_ascii=False), flush=True)
    json.dump(res, open(f"{D}/03_funding_carry/rezultatai.json", "w"), ensure_ascii=False, indent=1)
    print("CARRY_DONE")
