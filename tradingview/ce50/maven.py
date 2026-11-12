"""CE50 per Maven Omo 2-Step ($10k už $38), 2025-01-01 .. 2026-11-10.
Taisyklės (maventrading.com/omo-2-step ir FAQ, 2026-11-12): Phase 1 +6 %, Phase 2 +8 %, fiksuotas max nuostolis 8 % nuo pradinio balanso,
dienos nuostolis 4 %, ≥3 pelningos dienos (≥0,5 % pradinio) kiekvienoje fazėje ir kiekviename išmokėjimo cikle,
išmokėjimas kas 10 darbo dienų, 80 % pelno, mokestis grąžinamas su 3-iuoju išmokėjimu.
Rizika fiksuota: r % pradinio balanso sandoriui (stop = 1R). Sandoriai iš test.py (NAS100 1 min., su kaštais)."""
from pathlib import Path
import numpy as np, pandas as pd

T = pd.read_csv(Path(__file__).parent / "trades_signal_960.csv", index_col=0, parse_dates=True)
T = T[T.index >= "2025-01-01"]
SIZE, FEE = 10000, 38


def run(tr, r):
    acc, phase, bal, pdays, start, pays, payout_sum, log = 1, 1, 0.0, 0, None, 0, 0.0, []
    p1 = p2 = funded = 0
    for d, R in tr.R.items():
        pnl = R * r
        if pnl <= -4: bal = -99  # dienos limitas
        bal += pnl
        if pnl >= 0.5: pdays += 1
        if bal <= -8:
            log.append(f"{d:%Y-%m-%d} sąskaita #{acc} pralaimėta ({'Phase ' + str(phase) if phase < 3 else 'funded'})")
            acc += 1; phase, bal, pdays, pays = 1, 0.0, 0, 0; continue
        if phase == 1 and bal >= 6 and pdays >= 3:
            p1 += 1; log.append(f"{d:%Y-%m-%d} #{acc} Phase 1 praeita"); phase, bal, pdays = 2, 0.0, 0
        elif phase == 2 and bal >= 8 and pdays >= 3:
            p2 += 1; funded += 1; log.append(f"{d:%Y-%m-%d} #{acc} Phase 2 praeita -> funded"); phase, bal, pdays, start = 3, 0.0, 0, d
        elif phase == 3 and np.busday_count(start.date(), d.date()) >= 10 and bal > 0 and pdays >= 3:
            usd = 0.8 * bal / 100 * SIZE; pays += 1; payout_sum += usd + (FEE if pays == 3 else 0)
            log.append(f"{d:%Y-%m-%d} #{acc} išmokėjimas {usd:.0f} $"); bal, pdays, start = 0.0, 0, d
    state = {1: "Phase 1", 2: "Phase 2", 3: "funded"}[phase]
    return dict(r=r, accounts=acc, p1=p1, p2=p2, payouts=payout_sum, cost=acc * FEE, net=payout_sum - acc * FEE,
                now=f"{state}, balansas {bal:+.1f} %"), log


out = [f"CE50 per Maven Omo 2-Step $10k, {T.index[0]:%Y-%m-%d}..{T.index[-1]:%Y-%m-%d}"]
for lab, tr in (("Tik long", T[T.side > 0]), ("Long + short", T)):
    out.append(f"\n{lab} ({len(tr)} sandorių):")
    out.append(f"{'rizika':>7} {'nupirkta':>9} {'P1':>4} {'P2/funded':>10} {'išmokėta $':>11} {'išleista $':>11} {'grynai $':>9}  dabar")
    for r in (0.5, 0.75, 1.0, 1.5, 2.0):
        s, log = run(tr, r)
        out.append(f"{r:6.2f}% {s['accounts']:9} {s['p1']:4} {s['p2']:10} {s['payouts']:11.0f} {s['cost']:11.0f} {s['net']:9.0f}  {s['now']}")
        if lab == "Tik long" and r == 1.0: detail = log
out += ["\nĮvykiai (tik long, 1 % rizika):"] + detail
print("\n".join(out)); (Path(__file__).parent / "REZ_MAVEN.txt").write_text("\n".join(out))
