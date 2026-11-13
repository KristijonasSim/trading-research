# Trading research: kontekstas naujam botui

Atsakyk lietuviškai, trumpai, be barbarizmų. Detales rašyk į failus, ne į pokalbį.

## Tikslas
Rasti ir patikrinti **kitų žmonių jau sukurtas** prekybos strategijas (kripto ir akcijos, trumpalaikes ir ilgalaikes). **Savų strategijų nekuriame.**

## Testavimo taisyklės
1. Visos strategijos testuojamos tais pačiais duomenimis ir mokesčiais.
2. Lyginama su „pirkti ir laikyti“ (BTC/ETH, altcoin'ų krepšelis, akcijoms SPY).
3. Atmetama, jei strategija naudoja ateities duomenis (Freqtrade `lookahead-analysis`, `recursive-analysis`).
4. Testuojama viename laikotarpyje, tikrinama dar nematytame.
5. Kas išgyvena: dry-run / demo 1–2 mėn., tik tada mažos realios sumos.

## Svarbiausi failai
| Failas | Kas jame |
|---|---|
| `README.md` | Įrankių sąrašas ir šaltiniai |
| `results/SUVESTINE.md` | **Pradėk nuo čia.** Pagrindinės išvados, atrinktos strategijos, laukiantys sprendimai |
| `results/PROGRESS.md` | Darbų eiga su datomis (skriptai į jį rašo automatiškai) |
| `results/freqtrade_ranking.md` | Visų 65 strategijų lentelės pagal grupes ir metus |
| `results/freqtrade_all_results.csv` | Tie patys rezultatai CSV formatu |
| `results/validation/*.log` | Lookahead / recursive patikrų logai |

## Freqtrade (`freqtrade/`)
- Freqtrade 2026.10, Python 3.12, virtuali aplinka `freqtrade/.venv`.
- Konfigai: `config_spot.json` (mokestis 0,1 %), `config_futures.json` (0,05 %). Birža Binance, pradinis balansas 1000 USDT.
- Strategijos: `user_data/strategies/spot`, `.../futures`, `.../extra` (nepaleistos, žr. žemiau).
- Duomenys: `user_data/data` (jau atsiųsti, 2021-11-08 – 2026-11-08).
- Grupės: BTC+ETH ir top 10 altcoin'ų (XRP, BNB, SOL, DOGE, ADA, TRX, LINK, AVAX, LTC, DOT).

GitHub repo (github.com/KristijonasSim/trading-research) **neturi** šių failų, nes jie per dideli: `.venv/`, `user_data/data/`, `results/raw/`, `sources/` (klonuoti strategijų repo). Jei dirbi su nauja kopija, atkurk juos: `python3 -m venv .venv && .venv/bin/pip install freqtrade`, tada `freqtrade download-data` (Binance, 2021-11-08 – 2026-11-08, laikotarpiai 1m/5m/1h/4h).

Komandos (paleisti iš `freqtrade/`):
- `.venv/bin/python run_all.py -j 1`: visi backtestai. Baigtus praleidžia, todėl galima tęsti po perkrovimo (`-s <Strategija>` paleidžia vieną).
- `.venv/bin/python report.py`: sugeneruoja `results/freqtrade_ranking.md` ir CSV.
- `bash validate.sh`: lookahead/recursive patikros, logai rašomi į `results/validation/`.

## Būsena (2026-11-09)
- ✅ Atlikti 65 strategijų backtestai (oficialus `freqtrade-strategies` repo + NostalgiaForInfinityX8), 5 metai.
- ✅ Patikrintos 7 geriausios. Švarios: CombinedBinHAndCluc, ReinforcedAverageStrategy, Low_BB, VolatilitySystem (futures), UniversalMACD, BinHV45.
- ❌ NostalgiaForInfinityX8 atmesta, nes naudoja ateities duomenis (2 patikros: 4/18 ir 6/20 exit signalų).
- ⚠️ VolatilitySystem: +69,8 %/m., bet 2x svertas, be stop-loss, max kritimas 53 %.
- Geriausios saugesnės (altcoin'ai): CombinedBinHAndCluc +9,1 %/m., ReinforcedAverage +6,5 %/m., Low_BB +6,3 %/m. Altcoin'ų „pirkti ir laikyti“ per 5 m. iš 1000 USDT liktų 620.

## Laukia vartotojo sprendimo
1. **469 papildomos strategijos** `freqtrade/user_data/strategies/extra/` (HUGE_FreqTrade_Strategy_Collection, TheoBrigitte, i1ya, trendrider). **Nepaleistos:** kodas iš nežinomų autorių. `Ichi.py` kviečia `rm`, `Uptrend.py` naudoja `eval()`. **Nepaleisk be vartotojo leidimo.** Jei leis, saugiausia paleisti Docker konteineryje be interneto.
2. **Dry-run** 2–3 švarioms strategijoms (siūloma: CombinedBinHAndCluc, Low_BB, ReinforcedAverage ant altcoin'ų).
3. **VolatilitySystem** išbandyti saugesnę versiją (be sverto, su stop-loss).

## OctoBot ir QuantConnect (2026-11-09, kitas agentas)
- OctoBot: 18 robotų + grid ant indeksų/aukso. Nė vienas neverta → `results/octobot_ranking.md`.
- QuantConnect: biblioteka (25 strategijos) + forumas (60 versijų), Lean Docker lokaliai → `results/quantconnect_ranking.md`.
- **Atrinkti botai (≥14 %/m.): `best_strategies/ATRINKTI_BOTAI.md`.** Senas perdavimas: `best_strategies/README.md` (In & Out ten jau atmesta). Ką testuoti toliau (216 kandidatų): `results/TESTUOTI_TOLIAU.md`.**

## 2026-11-09 vakaras: patikros ir nauji testai
- **In & Out TQQQ/TMF atmesta.** Ankstesnis rezultatas (+13,1 %/m., 2022 +35 %) neatsikartoja. Lean perpaleidus: 2022 −55 %, kritimas 68 %. Pandas versija (`quantconnect-lean/scripts/inout_pandas.py`, rezultatai `quantconnect-lean/results/inout/`): 2021–2026 visos versijos (su klaida ir ištaisytos) pralaimi SPY; 2015–2021 puiku, bet tai autoriaus kūrimo laikotarpis. Priežastis: „išėjus“ laiko obligacijas su svertu, 2022 jos krito kartu su akcijomis. IBKR valandinių testas nebereikalingas.
- **CombinedBinHAndCluc išgyveno nematytą 2018–2021** (altcoin'ai): +12,1 %/m., teigiama kasmet, bet kritimas 38 % (ne 15 %). BTC+ETH netinka (−7 %/m.). Skriptas `freqtrade/run_oos.py`, rezultatai `results/oos_freqtrade.json`. Kitas žingsnis: dry-run.
- **Vartotojo TradingView „Volatility Breakout“** (`volbreakout/`): kaip parašytas, nelenkia laikymo nė viename rėme. Geriausias pritaikymas NAS100 1h +7 %/m., kritimas 8 %. Vartotojo paklausta, kaip TradingView matė pranašumą (laukiama atsakymo).
- **25 ETF strategijos** (`etf-rotation/`, 2008–2026): nė viena saugi nelenkia SPY/QQQ grąža, bet LAA, HAA, BAA-G12, Permanent Portfolio turi 2–3 kartus mažesnius kritimus (13–20 %) ir veikė po paskelbimo. Su svertu: TQQQ kai QQQ > 200 d. +24,5 %/m., kritimas 61 %.

## 2026-11-10: TradingView įrankiai (NAS100 scalping)
- **Geriausias: `tradingview/GERIAUSIAS_IRANKIS.md`** → `tradingview/Noise_Breakout_NAS100.pine` (Zarattini ir kt. 2024, kas 60 min.): 2021–24 +15 %/m., 2025–26 +7,7 %/m., kritimas ~6 %. Patikrinta TradingView.
- Atmesta: EI3v2 ant indeksų, ORB, intraday momentum, RSI(2)+VWAP, GER40, auksas, QQQ3+200 d. (2000–10 −90 %). Testai: `tradingview/scalp_test/`, `tradingview/qqq3_trend/`.

- QuantConnect forumas, 2 partija (17 temų, 74 versijos): nieko naujo, geri rezultatai buvo dėl paslėpto sverto klaidų → `results/quantconnect_forum2.md`. `run_lean.py` dabar palaiko ir naują QC API (snake_case).

- **EI3v2 ir E0V1E_DCA3 išlaikė nematytą 2018–2021** (ir su 2018 m. top 9 monetomis): +70 %/m., kasmet pliuse. Lieka dry-run. `best_strategies/ATRINKTI_BOTAI.md`.

- Akcijos (Industry Trends, S&P 500 momentum, Clenow, VIX/SVXY, Connors): nė viena patikimai nelenkia SPY 2015–26 → `industry-trends/AKCIJOS_REZULTATAI.md`. Kripto trendai (Concretum) netinka → `crypto-trend/REZULTATAI.md`.

- **E0V1E_DCA3 su svertu:** 3x +42 %/m., 10x +53 %/m., bet kritimai 52–71 % (2025-10-10 likvidacijos) → `freqtrade/results/lev/REZULTATAI.md`. Bybit demo botas paruoštas `~/trading/bybit_demo/` (raktai tik ten, ne repo; paleisti `./start.sh <svertas>`), 2026-11-10 paleistas E0V1E_DCA3 15x (demo, 49 % balanso); EI3v2 reikia atskiro Bybit subaccount rakto.

- 2026-11-11: `extra/` partijos iki batch50g (~350 iš 469). **NASOSv5_mod3 atrinkta** (alts10 +18,3 %/m., kritimas 3,3 %, išlaikė 2018–21). Kitą partiją: `freqtrade/make_batch.py batch50h`; 1m strategijos ant alts10 netelpa į RAM, praleidžiamos.

- 2026-11-12: `sources_more2` (25 repo, 425 strategijos) → batchM5–M13; **ckNSJT_morning atrinkta** (nr. 4), Ichimoku_v2/v5/v8/v16 rizikingų sąraše. Pristabdyta ties batchM10, tęsti `freqtrade/queue2.sh`.

- 2026-11-12/13: 10 Instagram įrašų patikrinta, vienintelis vertas – **CE 50% Model** (NQ) → `tradingview/ce50/REZULTATAI.md`, indikatorius `tradingview/CE50_NAS100_indikatorius.pine`. batchM10–M13 baigtos, tinkamų nėra. 89 naujos strategijos (`freqtrade/sources_more3`, partijos dar nesukurtos) laukia leidimo. Ataskaita: `results/ATASKAITA_2026-11-13.md`.

- 2026-11-13: svertas su 2020–21 (`freqtrade/results/lev3/`): EI3v2 3x ir NASOSv5 5x neatlaiko; EI3v2 1x/2x saugu, 2,4x riba. Aprašas GitHub: `best_strategies/EI3v2/README.md`.

- 2026-11-13 vakaras: **MACDVStrategy atrinkta** (BTC+ETH 1d, +16 %/m., kritimas 15 %, 2018–21 +73 %/m.). Savaitgalio testai: `results/SAVAITGALIS.md`, straipsnių eilė `papers/EILE.md`.

## Dar nepradėta
Aplankai `ib_async/`, `vectorbt/`, `backtesting-py/` tušti.

## Darbo tvarka
- Kiekvieną atliktą darbą įrašyk į `results/PROGRESS.md` su data.
- Svarbias išvadas atnaujink `results/SUVESTINE.md`.
- Šį failą atnaujink, kai pasikeičia būsena ar atsiranda naujų sprendimų.
