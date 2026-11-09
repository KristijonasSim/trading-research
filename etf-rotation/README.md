# ETF rotacijos / paskirstymo strategijos (2026-11-09)

Kodas `etf.py`, duomenys Yahoo (su dividendais) + FRED nedarbo lygis (`data/`), rezultatai `results/summary.md`, `results/equity.csv`.

## Taisyklės
- Signalas mėnesio paskutinės dienos uždarymu, sandoris kitos dienos atidarymu. Mokestis 0,1 %. „Grynieji“ = BIL.
- Laikotarpis 2008-07 – 2026-11 (kai kurios nuo 2008-11 / 2009 / 2011, kai atsirado ETF).
- „Po paskelbimo“ = tik metai po to, kai autorius strategiją paskelbė (tikrai nematyti duomenys).
- Supaprastinimai: AAA min. dispersija → atvirkštinis svyravimas; DAA-G4 = „Canary“ variantas.

## Pagrindiniai rezultatai (2008-07 – 2026-11)
| Strategija | %/m | Max kritimas | 2008 krizė | 2022 | Po paskelbimo %/m |
|---|---|---|---|---|---|
| Laikyti SPY | 12,0 | 47 % | −46 % | −18 % | – |
| Laikyti QQQ | 16,6 | 47 % | −44 % | −33 % | – |
| 60/40 | 8,6 | 29 % | −28 % | −16 % | – |
| **Lethargic Asset Allocation** | 9,7 | **20 %** | −12 % | −14 % | 10,0 (nuo 2020) |
| **HAA** | 9,0 | **13 %** | −3 % | +3 % | 9,5 (nuo 2024) |
| **BAA-G12** | 8,1 | **14 %** | – | 0 % | 5,8 (nuo 2023) |
| Permanent Portfolio | 6,7 | 18 % | −8 % | −14 % | – |
| TQQQ kai QQQ > 200 d. | 24,5 | 61 % | – | −44 % | 32,6 (nuo 2020) |
| HFEA UPRO/TMF | 20,2 | 71 % | – | −64 % | 6,7 (nuo 2020) |
| GEM Dual Momentum | 7,5 | 34 % | +4 % | −17 % | 6,8 (nuo 2015) |

## Išvada
- Nė viena saugi strategija neuždirba daugiau nei laikyti SPY/QQQ. Jų nauda: 2–3 kartus mažesni kritimai (13–20 % vietoj 47 %).
- Geriausias grąžos ir rizikos santykis (Sharpe): LAA, Permanent Portfolio, BAA-G12, HAA. Po paskelbimo jos veikė panašiai kaip anksčiau (nesubyrėjo).
- Daugiau grąžos tik su svertu: TQQQ + 200 d. taisyklė (+24,5 %/m., bet kritimas 61 %).
