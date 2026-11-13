#!/usr/bin/env python3
"""#15 Kripto žemo volatilumo anomalija (Burggraf, Rudolf 2021) ir #16 MAX / loterijos efektas (Li ir kt. 2021).
Visata: top 50 Binance USDT porų pagal 30 d. apyvartą (su išregistruotomis), variklis ../xsec.py, mokestis 0,1 %.
Signalas didesnis = pirkti: −30 d. volatilumas; −MAX (didžiausia dienos grąža per 30 d.).
Kūrimo 2018–2021, nematytas 2022–2026."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from xsec import load, run, stats
P, V = load()
R = lambda p: p.pct_change(fill_method=None)
btc = P["BTCUSDT"] / P["BTCUSDT"].iloc[0]
T = {
    "BTC laikyti": lambda: btc,
    "Top50 lygiais svoriais": lambda: run(P, V, lambda p: R(p), 7, side="bench"),
    "15 Žemas vol 30 d., long 20 %, kas sav.": lambda: run(P, V, lambda p: -R(p).rolling(30, min_periods=20).std(), 7),
    "15 Žemas vol 30 d., long 20 %, kas mėn.": lambda: run(P, V, lambda p: -R(p).rolling(30, min_periods=20).std(), 28),
    "15 Žemas vol, long-short": lambda: run(P, V, lambda p: -R(p).rolling(30, min_periods=20).std(), 7, side="ls"),
    "15 Aukštas vol, long 20 %": lambda: run(P, V, lambda p: R(p).rolling(30, min_periods=20).std(), 7),
    "16 Mažas MAX, long 20 %": lambda: run(P, V, lambda p: -R(p).rolling(30, min_periods=20).max(), 7),
    "16 Mažas MAX, long-short": lambda: run(P, V, lambda p: -R(p).rolling(30, min_periods=20).max(), 7, side="ls"),
    "16 Didelis MAX, long 20 %": lambda: run(P, V, lambda p: R(p).rolling(30, min_periods=20).max(), 7),
    "15 Žemas vol, top 20 visata": lambda: run(P, V, lambda p: -R(p).rolling(30, min_periods=20).std(), 7, topn=20),
}
rows = []
out = {}
for k, f in T.items():
    e = f(); a = stats(e, "2018-03-01", "2022-01-01"); b = stats(e, "2022-01-01", "2026-12-01")
    out[k] = dict(a=a, b=b); print(k, a["cagr"], a["dd"], "|", b["cagr"], b["dd"], b["yearly"], flush=True)
    rows.append(f"| {k} | {a['cagr']:+.1f} | {a['dd']:.0f} | {b['cagr']:+.1f} | {b['dd']:.0f} | {' '.join(f'{y}:{v}' for y, v in b['yearly'].items())} |")
md = "| Strategija | 2018–21 %/m | kritimas | 2022–26 %/m | kritimas | metai 2022–26 % |\n|---|---|---|---|---|---|\n" + "\n".join(rows)
open("REZULTATAI.txt", "w").write(md + "\n"); json.dump(out, open("rezultatai.json", "w"), indent=1)
