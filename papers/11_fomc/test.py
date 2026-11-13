#!/usr/bin/env python3
"""#11 Pre-FOMC dreifas (Lucca, Moench 2015, J. Finance): S&P 500 kyla per 24 val. prieš FOMC sprendimą.
FOMC planiniai posėdžiai (federalreserve.gov), sprendimo diena = paskutinė posėdžio diena.
Dienos duomenys (Yahoo SPY): A) laikyti nuo dienos prieš uždarymo iki sprendimo dienos uždarymo,
B) nuo uždarymo t-2 iki t-1 (be paties sprendimo), C) sprendimo dienos atidarymas -> uždarymas.
Periodai: 1994–2011 (straipsnio), 2012–2026 (po). Mokestis 0,05 % į abi puses."""
import re, glob, numpy as np, pandas as pd
M = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"], 1)}
Ms = {k[:3]: v for k, v in M.items()}
days = set()
for f in sorted(glob.glob("data/h*.htm")):
    for t in re.findall(r"<h5[^>]*>([^<]*Meeting[^<]*)", open(f, errors="ignore").read()):
        m = re.match(r"\s*(.+?)\s+Meeting\s*-\s*(\d{4})", t)
        if not m: continue
        s, y = m.group(1), int(m.group(2))
        if "unscheduled" in s or "cancelled" in s: continue
        tok = s.split()
        if "/" in tok[0]: mon = Ms[tok[0].split("/")[1][:3]]; d = int(tok[1].split("-")[-1])
        elif len(tok) == 3: mon = Ms[tok[1].split("-")[-1][:3]]; d = int(tok[2])   # "January 31-February 1"
        else: mon = Ms[tok[0][:3]]; d = int(tok[1].split("-")[-1])
        days.add(pd.Timestamp(y, mon, d))
html = open("data/cal.htm", errors="ignore").read()
for blk in re.split(r"(\d{4}) FOMC Meetings", html)[1:]:
    pass
parts = re.split(r"(\d{4}) FOMC Meetings", html)
for y, body in zip(parts[1::2], parts[2::2]):
    for mon, dd in re.findall(r'fomc-meeting__month[^>]*><strong>([^<]+)</strong>.*?fomc-meeting__date[^>]*>([^<]+)<', body, re.S):
        mon = mon.split("/")[-1].strip(); dd = dd.strip().rstrip("*").split("-")[-1].strip()
        if not dd[:2].strip().isdigit(): continue
        mm = M.get(mon) or Ms.get(mon[:3])
        if mm: days.add(pd.Timestamp(int(y), mm, int(re.match(r"\d+", dd).group())))
F = sorted(d for d in days if pd.Timestamp("1994-01-01") <= d <= pd.Timestamp("2026-11-12"))
print("FOMC sprendimų:", len(F), F[:2], F[-2:])

import yfinance as yf, os
if not os.path.exists("data/spy.pkl"):
    yf.download("SPY", start="1993-01-01", end="2026-11-13", auto_adjust=True, progress=False).to_pickle("data/spy.pkl")
D = pd.read_pickle("data/spy.pkl"); D.columns = D.columns.get_level_values(0)
c, o = D.Close, D.Open; idx = c.index
r = c.pct_change()
fi = [idx.searchsorted(d) for d in F if d in idx]
FEE = 0.0005
A = pd.Series(0.0, idx); B = pd.Series(0.0, idx); Cc = pd.Series(0.0, idx)
for i in fi:
    A.iloc[i] = r.iloc[i] - 2 * FEE
    B.iloc[i - 1] = r.iloc[i - 1] - 2 * FEE
    Cc.iloc[i] = c.iloc[i] / o.iloc[i] - 1 - 2 * FEE
rows = []
for a, b in [("1994", "2011"), ("2012", "2026"), ("2016", "2026")]:
    for k, s in [("A: t-1 uždarymas → sprendimo d. uždarymas", A), ("B: t-2 → t-1 (prieš sprendimą)", B), ("C: sprendimo d. atidarymas → uždarymas", Cc)]:
        ev = s[a:b][s[a:b] != 0]
        rest = r[a:b].drop(ev.index, errors="ignore")
        tstat = ev.mean() / ev.std() * np.sqrt(len(ev))
        ann = (1 + s[a:b]).prod() ** (1 / ((pd.Timestamp(b + "-12-31") - pd.Timestamp(a)).days / 365.25)) - 1
        rows.append((f"{a}–{b}", k, len(ev), round(ev.mean() * 100, 3), round(tstat, 2), round(rest.mean() * 100, 3), round(ann * 100, 2), round((ev > 0).mean() * 100)))
df = pd.DataFrame(rows, columns=["periodas", "langas", "įvykių", "vid. % (po mokesčio)", "t-stat", "kitos dienos vid. %", "%/m tik šiomis d.", "teigiamų %"])
yr = A[A != 0]; yr = yr.groupby(yr.index.year).sum().mul(100).round(2)
out = df.to_markdown(index=False) + "\n\nA lango suma pagal metus (%):\n\n" + yr.to_frame("A").T.to_markdown()
print(out); open("REZULTATAI.txt", "w").write(out + "\n")
