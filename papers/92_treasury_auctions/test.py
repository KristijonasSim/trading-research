"""92: Iždo aukcionų ciklas (Lou, Yan, Zhang 2013 RFS „Anticipated and Repeated Shocks in Liquid Markets“): obligacijų kainos krenta ~5 d. prieš aukcioną
ir atsigauna po jo. Taisyklės: A) long TLT/IEF nuo aukciono dienos uždarymo 5 d.; B) vengti 5 d. prieš aukcioną (kitu metu long); C) A − (prieš aukcioną short).
Aukcionai: TreasuryDirect (competitiveAuctionCloseDate) 10-Year, 20-Year, 30-Year (TLT), 5/7/10-Year (IEF). Kaštai 0,03 %, kitu metu BIL.
Paskelbta 2013 -> nematytas 2013–2026. Paleisti: quantconnect-lean/.venv/bin/python papers/92_treasury_auctions/test.py"""
import json, os, numpy as np, pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(D)
A = json.load(open(f"{D}/data/note.json")) + json.load(open(f"{D}/data/bond.json"))
au = pd.DataFrame([(pd.to_datetime(x["competitiveAuctionCloseDate"]), x["originalSecurityTerm"]) for x in A if x.get("competitiveAuctionCloseDate")], columns=["d", "term"])
L = lambda t: pd.read_csv(f"{R}/59_ibs/data/{t}.csv", index_col=0, parse_dates=True).Close
bil = L("BIL").pct_change()
def st(x, a, b):
    x = x[a:b]; e = (1 + x).cumprod(); n = len(x) / 252; return f"{(e.iloc[-1] ** (1 / n) - 1) * 100:+5.1f}% kr {(e / e.cummax() - 1).min() * 100:3.0f}%"
PER = [("2004", "2012"), ("2013", "2019"), ("2020", "2026")]
print("periodai: 2004–12 | 2013–19 | 2020–26")
for etf, terms in (("TLT", ["10-Year", "20-Year", "30-Year"]), ("IEF", ["5-Year", "7-Year", "10-Year"])):
    c = L(etf); c = c[c.index >= "2004-01-01"]; r = c.pct_change().fillna(0); cash = bil.reindex(c.index).fillna(0)
    days = pd.DatetimeIndex(sorted(set(au[au.term.isin(terms)].d))); pos_idx = c.index.searchsorted(days)
    after = pd.Series(0.0, c.index); before = pd.Series(0.0, c.index)
    for k in pos_idx:
        if k < len(c): after.iloc[k + 1:k + 6] = 1; before.iloc[max(0, k - 4):k + 1] = 1     # po: 5 d. grąžos nuo aukciono uždarymo; prieš: 5 d. iki aukciono imtinai
    print(f"\n{etf} aukcionų {len(days)}; vid. dienos grąža bp prieš / po / kitos: " + " | ".join(f"{r[before == 1][a:b].mean()*1e4:+.1f} / {r[after == 1][a:b].mean()*1e4:+.1f} / {r[(before == 0) & (after == 0)][a:b].mean()*1e4:+.1f}" for a, b in PER))
    print(f"  {'laikyti':28s} " + " | ".join(st(r, a, b) for a, b in PER))
    for nm, pos in (("A 5 d. po aukciono", after), ("B visada, išskyrus 5 d. prieš", 1 - before.clip(upper=1)), ("C po long, prieš short", after - before)):
        pos = pos.clip(-1, 1); x = pos * r + (1 - pos.abs()) * cash - pos.diff().abs().fillna(0) * 0.0003
        print(f"  {nm:28s} " + " | ".join(st(x, a, b) for a, b in PER) + f" | rinkoje {pos.abs().mean()*100:.0f}%")
    if etf == "TLT":
        r3 = 3 * r - 2 * cash - 0.0095 / 252                     # sintetinis 3x TLT (≈ TMF)
        print(f"  {'3x TLT (sint.) laikyti':28s} " + " | ".join(st(r3, a, b) for a, b in PER))
        for nm, pos in (("3x: B išskyrus 5 d. prieš", 1 - before.clip(upper=1)), ("3x: C po long, prieš short", after - before)):
            pos = pos.clip(-1, 1); x = pos * r3 + (1 - pos.abs()) * cash - pos.diff().abs().fillna(0) * 0.0005
            print(f"  {nm:28s} " + " | ".join(st(x, a, b) for a, b in PER) + f" | 2013–26 {st(x, '2013', '2027')}")
