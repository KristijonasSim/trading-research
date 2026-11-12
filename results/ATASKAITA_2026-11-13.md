# Rytinė ataskaita 2026-11-13

## Naktį
- Bybit demo botas (E0V1E_DCA3 15x) veikia nuo 2026-11-12 17:32.
- Baigtos partijos batchM10–M13 (sources_more2, ~165 strategijos). **Naujų tinkamų nėra.** Visi „super“ rezultatai žiūrėjo į ateitį:
  NOTankAi (argrelextrema), Peekaboo (find_peaks), HurstCycle (center=True, FFT), grad (np.gradient); lw_tdw_tdm – kalendoriaus dienos pritaikytos prie istorijos.
- Paruošta 89 naujos strategijos iš 33 GitHub repo (`freqtrade/sources_more3/new_strategies.txt`), **nepaleistos – reikia vartotojo leidimo** (svetimas kodas; būtų Docker be interneto).

## Vakar (Instagram patikros)
| Įrašas | Išvada |
|---|---|
| Nakties dėžės pusė (NQ) | 81/75 % tiesa, bet prekiaujant minusas |
| Kronos AI modelis | nepaleistas (blokuoja saugumo filtras) |
| day-trader-skill (ORB) | minusas kasmet |
| 8 trailing stop būdai | nė vienas nepagerina Noise Breakout |
| Efektyvi riba | nelenkia paprasto 60/40 |
| Absorbcija (delta) | filtras nieko neprideda |
| **CE 50% Model (NQ)** | **veikia**: 10/11 m. pliuse, 2022–26 +17 %/m. prie 1 % rizikos, kritimas 25 % |
| Composite profilis | zonos greičio nenumato |
| GPT6 Astra | netestuojama |
| 30 d. vidurkis nuo 1926 | veikė tik iki 1975 |

CE50: TradingView indikatorius `tradingview/CE50_NAS100_indikatorius.pine`; Maven Omo simuliacija – max ~0,3 praeito challenge per mėn. (žr. `tradingview/ce50/REZULTATAI.md`).

## Laukia sprendimo
1. Leisti 89 naujas strategijas (N partijos)?
2. CE50 + Noise Breakout į demo?
3. Kronos testą paleisti pačiam (`! cd ~/Desktop/trading-research/kronos && .venv/bin/python test.py BTC`)?
