# Tyrimo eiga (atnaujinama automatiškai)

Jei kompiuteris išsijungė: visi rezultatai išsaugoti šiame aplanke. Skriptai tęsia nuo ten, kur sustojo:
- `cd ~/Desktop/trading-research/freqtrade && .venv/bin/python run_all.py -j 1` (backtestai)
- `bash validate.sh` (lookahead/recursive patikros)

## Atlikta
- 2026-11-08: 65 Freqtrade strategijų backtestai (5 m., BTC+ETH ir top 10 altcoin'ų) → `freqtrade_ranking.md`, `freqtrade_all_results.csv`
- 2026-11-08: VolatilitySystem (futures, BTC+ETH, 2022) lookahead: be ateities duomenų naudojimo

## Naktinis darbas
- 2026-11-08 23:16 validation NFI_X8_alts: lookahead bias = Yes (log: results/validation/NFI_X8_alts.log)
- 2026-11-08 23:17 validation CombinedBinHAndCluc_alts: lookahead bias = No (log: results/validation/CombinedBinHAndCluc_alts.log)
- 2026-11-08 23:17 validation ReinforcedAverage_alts: lookahead bias = No (log: results/validation/ReinforcedAverage_alts.log)
- 2026-11-08 23:17 validation Low_BB_alts: lookahead bias = toofewtradescaught(0/10).Testfailed. (log: results/validation/Low_BB_alts.log)
- 2026-11-08 23:17 validation BinHV45_btc_eth: lookahead bias = toofewtradescaught(0/10).Testfailed. (log: results/validation/BinHV45_btc_eth.log)
- 2026-11-08 23:18 validation UniversalMACD_btc_eth: lookahead bias = No (log: results/validation/UniversalMACD_btc_eth.log)
- 2026-11-08 23:18 validation VolatilitySystem_alts: lookahead bias = No (log: results/validation/VolatilitySystem_alts.log)
- 2026-11-08 23:25 NFI X8 lookahead = Yes (4 iš 18 exit signalų skiriasi). Paleista pakartotinė patikra kitais periodais.
- 2026-11-08 23:25 469 papildomos strategijos (HUGE collection, TheoBrigitte, i1ya, TrendRider) surinktos į user_data/strategies/extra, bet NEPALEISTOS: nepatikrintas kodas iš nežinomų autorių, saugumo filtras sustabdė. Reikia vartotojo sprendimo.
- 2026-11-08 23:19 validation NFI_X8_btc_eth_2024: lookahead bias = toofewtradescaught(0/10).Testfailed. (log: results/validation/NFI_X8_btc_eth_2024.log)
- 2026-11-08 23:20 validation NFI_X8_alts5_2023: lookahead bias = toofewtradescaught(0/10).Testfailed. (log: results/validation/NFI_X8_alts5_2023.log)
- 2026-11-08 23:21 validation Low_BB_alts5_2024: lookahead bias = No (log: results/validation/Low_BB_alts5_2024.log)
- 2026-11-08 23:23 validation BinHV45_alts5_2024: lookahead bias = No (log: results/validation/BinHV45_alts5_2024.log)
- 2026-11-08 23:24 validation NFI_X8_alts10_2025: lookahead bias = Yes (log: results/validation/NFI_X8_alts10_2025.log)
- 2026-11-08 23:30 NFI X8 pakartotinė patikra (10 alts, 2025): bias = Yes (6/20 exit signalų). NFI atmesta.
- 2026-11-08 23:30 Low_BB ir BinHV45 (5 alts, 2024): bias = No.
- 2026-11-08 23:30 Galutinė suvestinė: results/SUVESTINE.md. Naktinis darbas baigtas.

## OctoBot
- 2026-11-09: OctoBot 2.1.1 (`octobot/`), jo paties backtesteris. 7 profiliai × 2 grupės, tie patys duomenys/datos/mokestis/1000 USDT → `octobot_ranking.md`, `octobot_all_results.csv`. „Pirkti ir laikyti“ sutampa su Freqtrade (−4,5 %/m. BTC+ETH, 624 alts), t. y. duomenys tie patys.
- Simple DCA neištestuotas: OctoBot backtesteris nepalaiko „pirkti pagal laiką“.
- Grid / Staggered nustatymai skirti BTC doleriais, todėl kitoms monetoms perskaičiuoti tuo pačiu % atstumu.
- Paleidimas: `cd octobot && scripts/run_group.sh btc_eth` (ir `alts10`), tada `.venv/bin/python scripts/report.py`.
- 2026-11-09: + 14 Daily Trading variantų (po vieną OctoBot indikatorių) × 2 grupės. 3 indikatoriai vieni neprekiauja (KlingerReversal, RSIWeight, InstantMA: skirti Dip Analyser / realaus laiko). Market Making nepalaiko kelių porų → neištestuota. Neveikę paleidimai: `octobot/results/not_supported/`.
- 2026-11-09: Grid / Trailing Grid / Staggered Orders ant US30, NAS100, S&P 500, aukso (XAU). Duomenys: Dukascopy 1h (`octobot/scripts/fetch_tradfi.py`, `make_tradfi_data.py`), tas pats OctoBot backtesteris, 0,1 % mokestis, 1000 start. Visi 3 pralaimi „pirkti ir laikyti“ visose 4 rinkose: kaina išeina iš tinklelio ir robotas sėdi grynuosiuose (0 % metai). → `octobot_ranking.md`

## 2026-11-09
- TradingView: supaprastintas LonesomeTheBlue „Trend Following Moving Averages“ → `tradingview/trend_ma_one_line.pine` (viena linija, žalia/raudona kai visi 20 MA sutampa, filtrai prieš netikrus signalus). TradingView neišbandyta.

## QuantConnect Lean
- 2026-11-09: QuantConnect Strategy Library (83 strategijos, kodas iš quantconnect.com puslapių → `quantconnect-lean/sources/strategies`). Tinka 25 (tik kainos). Lean Docker lokaliai, be interneto. Dienos: Yahoo (su dividendais), valandinės: Dukascopy. 0,1 % mokestis, 2021-11-08 – 2026-11-08. → `quantconnect_ranking.md`
- Techniniai suderinimai su nauju Lean (logika nekeista): datos/pinigai, Decimal→float, `self.benchmark` pervadinta, FB→META, UTX→RTX duomenys, 19: išmesti išbraukti bankai.
- Nepavyko: 02 (senas pandas), 1025 (tik valandinė, nėra SSO/SHY valandinių), 1031 SVM (per lėta). Valandinės tik ten, kur Dukascopy turi visus tickerius.
- Paleidimas: `cd quantconnect-lean && scripts/run_all.sh 6 && .venv/bin/python scripts/report.py`
- Trend Konsensusas: 8 metodai, 22 instrumentai, nematytas laikotarpis. Detalės `results/trend_konsensusas.md`. AI kNN indikatorius atmestas (50 %).
- 2026-11-09: QuantConnect forumas: 5 populiarios temos (9632 In & Out, 10039 Dual Momentum Out Days, 7708 Levered ETFs IRA, 5124 3X ETF Short Hedge, 2278 TQQQ/SQQQ volatility). 104 versijos → 60 paleidžiamų (tik ETF kainos), tik dieninės (valandinių šiems ETF nėra nemokamai). 11 neprekiavo (reikia dienos vidurio kainų), 2 nepasileido. Kodas: `quantconnect-lean/sources/forum/`, skriptas `scripts/scrape_forum.py`.
- 2026-11-09: Trend Konsensusas patikrintas 1h/4h/15m/5m NAS100 (NQ). Netinka dienos prekybai.
- 2026-11-09: patikrinta „BUY ties TP2 po SELL“ idėja – pagerina (77 % instrumentų).
- 2026-11-09: trailing stop virš TP2 patikrintas – nepagerina.
- 2026-11-09: platus trailing toli virš TP2 – lygu su „laikyti iki SELL“.
- 2026-11-09: Trend Konsensusas B ištestuotas 22 ETF.

## 2026-11-09 vakaras (kitas Claude seansas)
- In & Out perrašyta į pandas (`quantconnect-lean/scripts/inout_pandas.py`), 2015–2021 ir 2021–2026, 4 variantai. Lean perpaleidimas (originalus kodas, 2021–2026): +12,5 %/m., bet 2022 −55 %, kritimas 68 % (`quantconnect-lean/results/inout/lean_rerun_2021_2026.json`). Atmesta.
- `run_lean.py`: testavimo langas keičiamas per LEAN_START / LEAN_END.
- Freqtrade nematytas 2018–2021 (`freqtrade/run_oos.py`): CombinedBinHAndCluc alts +12,1 %/m. (kritimas 38 %), btc_eth −7,3 %; ReinforcedAverage alts +49 %/m.; UniversalMACD btc_eth +20,8 %/m.
- Volatility Breakout (vartotojo Pine) 5 rinkos × 4 rėmai, Dukascopy 15m 2017–2026 → `volbreakout/README.md`.
- 25 ETF strategijos 2008–2026 → `etf-rotation/README.md`.

## 2026-11-10 naktis: batch50c (tarpiniai, 63/100 baigta)
- NOTankAi_15 (+884 %/m., 100 % laimi) atmesta: `argrelextrema` žiūri 5 žvakes į ateitį.
- Rsiqui (+54,6 %/m. BTC+ETH) atmesta: `np.gradient` (centrinis skirtumas) naudoja kitos žvakės RSI.
- PrawnstarOBV (+42,6 %/m. alts10) atmesta: kritimas 63 %, 4 nuostolingi metai, viską neša 2023–2024.

## 2026-11-10: EI3v2 TradingView indikatorius
- `tradingview/EI3v2_tag_cofi_green.pine` (Pine v6): BUY su TP (trailing įsijungimo kaina ~+1,4 %), SELL su rezultatu ir priežastimi (TP / signalas / unclog). Freqtrade apsaugos (MaxDrawdown, LowProfitPairs ir kt.) neperkeltos. TradingView neišbandyta (MCP neprisijungė).
- Indikatorius pritaikytas bet kuriai rinkai (vartotojo prašymu NAS100): % ribos dauginamos iš mastelio k = grafiko 5m žvakės mediana / 0,26 % (altcoin'ų mediana 2024–2026). Rinkos filtras ne kripto rinkoms = pats grafikas (1h RSI8). Ištaisyta klaida: TP išėjimas įėjimo žvakėje rodė −0,2 %. Su k ≠ 1 tai jau pritaikymas, netestuotas.

## 2026-11-10: scalping ant indeksų (NAS100/SPX500/US30, 5m)
- EI3v2 ant NAS100 netinka (−2,4 %/m.; geriausias iš 480 variantų +3,4 %/m.). ORB ir intraday momentum netinka.
- **Noise Breakout (Zarattini, Aziz, Barbon 2024) NAS100: +12 %/m., kritimas 10 %, kasmet teigiama**, bet 2025+ tik +6 %/m. ir labai jautri spread'ui. SPX500/US30 silpna.
- TradingView: `tradingview/Noise_Breakout_NAS100.pine`. Detalės: `tradingview/scalp_test/REZULTATAI.md`.
- Noise Breakout indikatorius: vietoj skaičių žymės BUY/SELL ir „✓ Pelnas / ✗ Nuostolis“ (skaičiai užvedus pelę), SL linija (pasislenka kas 30 min.) ir TP linija (0,5 % = vid. pelningas sandoris; pagal nutylėjimą tik orientyras, galima įjungti uždarymą pasiekus TP, netestuota).
- Noise Breakout v3: patikrinimai kas 60 min. (2025–26: +7,7 %/m., kritimas 6,5 % vs 6,2 % ir 10,2 %), viena SL ir viena TP linija, ribos paslėptos, 15m = 5m. Trendo filtras ir platesnės ribos nepadėjo.
- Noise Breakout v3 patikrintas TradingView (Pepperstone NAS100 15m, per Chrome): kompiliuojasi be klaidų, rodo BUY/SELL, vieną SL ir vieną TP liniją, „✓ Pelnas / ✗ Nuostolis“. TV istorijoje: 72 sandoriai, laimi 37,5 %, iš viso +0,27 % (silpnas 2026 m., atitinka backtestą).
- Atšokimo scalperis RSI(2)+VWAP ant NAS100/SPX500 5m/15m: laimi 55–60 %, bet nuostolingas visuose variantuose. Netinka.
- Kitos rinkos: Noise Breakout GER40 ~+4 %/m., auksas ~0 %. Dydis pagal svyravimą nepagerino. QQQ3 + 200 d. vidurkis: 2000–10 −90 % (sintetinis 3x nuo 1999), nesaugu.
- **Galutinis įrankis: `tradingview/GERIAUSIAS_IRANKIS.md`** (Noise Breakout NAS100, kas 60 min.).

## 2026-11-10: QuantConnect forumas, 2 partija
- 17 naujų temų, 74 versijos per Lean. Geriausios (In & Out +12,4 %/m.) – dėl paslėpto 2x sverto klaidos; ištaisius +0,5…+1,6 %/m.
- In & Out signalas pandas 2008–26: po paskelbimo (2021–26) su grynaisiais +6,5 %/m. (kritimas 17 %) vs QQQ +11,2 % (35 %). 3x versija +6 %, kritimas 50 %.
- `run_lean.py` palaiko naują QuantConnect API. Detalės: `results/quantconnect_forum2.md`.

## 2026-11-10: Concretum kripto trendai (tikslas ≥ 20 %/m.)
- Catching Crypto Trends (Binance, 530 porų, be išgyvenusiųjų iškraipymo): 2018–21 +12,5 %/m., 2021–26 +2,4 %/m., po paskelbimo +0,7 %/m.; su 2x rizika +4,7 %/m. Netinka.
- Noise Breakout ant BTC/ETH/SOL 5m: nuostolinga. Detalės: `crypto-trend/REZULTATAI.md`.

## 2026-11-10: EI3v2 ir E0V1E_DCA3 – nematytas 2018–2021
- Dabartinis top 10: EI3v2 +134,7 %/m. (kritimas 16 %), E0V1E_DCA3 +91 %/m.; kiekvienais metais pliuse, net 2018.
- 2018 m. top 9 (be išgyvenusiųjų iškraipymo): EI3v2 +71 %/m. (17 %), E0V1E_DCA3 +70 %/m. (5 %).
- 1 min. detalumas 2020 m. sumažina pelną ~¼. Išlaikė. Detalės `best_strategies/ATRINKTI_BOTAI.md`.

## 2026-11-10: Industry Trends (Zarattini & Antonacci 2024)
- Ken French 48 šakų, 1926–2026. Kopija atitinka straipsnį (+17,5 vs +18,5 %/m. 1926–2024), bet nuo 2015 m. +6–7 %/m. vs rinka +13 %, po paskelbimo +2–3 % vs +17 %. Netinka. `industry-trends/REZULTATAI.md`.

## 2026-11-10: akcijų strategijų ratas (momentum, Clenow, VIX, Connors)
- Nė viena po kaštų patikimai nelenkia SPY 2015–26. Artimiausios: S&P 500 momentum top 50 kas sav. (≈ rinka), Connors RSI(2) 2x (rinkos grąža, kritimas perpus mažesnis, bet 2011–18 silpna), SVXY+VIX filtras (≈ SPY po 2018). `industry-trends/AKCIJOS_REZULTATAI.md`.
- RSI(2) ant 17 ETF: ~+7 %/m., kritimas 10–13 %, 2011–18 +2 %. Nelenkia rinkos.
- 2026-11-10: E0V1E_DCA3 su svertu (futures): 1x +16 %/m. krit. 6 %; 3x +42 %/m. krit. 52 %; 10x +53 %/m. krit. 71 %, likvidacijos 2025-10-10. → `freqtrade/results/lev/REZULTATAI.md`. Bybit demo konfigas paruoštas (`~/trading/bybit_demo/`, ne repo).
- 2026-11-10: EI3v2 + E0V1E_DCA3 po 50 %: 2021–26 +21,3 %/m., kritimas 6,4 %; 2018–21 +70,5 %/m., kritimas 7,8 %. → `freqtrade/results/combo/REZULTATAI.md`
- 2026-11-10 14:03: Bybit demo paleistas E0V1E_DCA3, 15x, isolated, 49 % iš 500 USDT (`~/trading/bybit_demo/`, log bot.log). EI3v2 laukia antro (subaccount) API rakto.

## 2026-11-10: batch50d (4-a partija, 50 strategijų iš `extra/`, A–B)
- 100 testų: 59 pavyko, 41 nepasileido (10 – nėra 1m duomenų, 8 – trūksta bibliotekų, kiti – kodo klaidos).
- Geriausios: BigZ0407HO alts10 +7,6 %/m. (kritimas 6,5 %), BinClucMadV1 alts10 +6,9 %/m. (3,7 %). Naujų atrinktų nėra.
- `run_batch.py` dabar perduoda `--timeframe` (senos strategijos turi tik `ticker_interval`); 15m duomenys sudaryti iš 5m; atkurtas `docker_offline/binance_markets.json` ir Docker vaizdas.
- 2026-11-10: batch50e (5-a partija) sustabdyta vartotojo prašymu, baigta 50/100 testų. Geriausia ClucHAnix_5m alts10 +16,4 %/m., kritimas 22 %, 2025 −10,6 % – silpnesnė už atrinktus. Tęsti: `BATCH=batch50e run_batch.py` (baigtus praleidžia).
- 2026-11-10: Swing Trend Pullback indikatorius (RSI(2) atšokimas / 20 d. lūžis + Chandelier stop, tik kai EMA50 > EMA200): 19 rinkų 2005–14 +6,4 %/m. (kritimas 29 % vs laikant 58 %), 2015–26 +6,8 % vs laikant +13,4 %. `tradingview/swing/REZULTATAI.md`.
- 2026-11-10: Swing Trend Pullback patobulinta (RSI(2)<25, 5 ATR stop, be trendo išėjimo): 2005–14 +8,1 %/m. (krit. 35 % vs 58 %), 2015–26 +10,4 % (32 % vs 41 %). Patikrinta TradingView SPY: 81 sandoris, laimi 59 %, +1704 % vs laikant +1523 %.
- 2026-11-10: Swing Trend Pullback palygintas su 7 populiariais indikatoriais (Supertrend, Golden cross, MACD, PSAR, Turtle, EMA 9/21): 1 vieta abiem laikotarpiais. Išsaugota TradingView.
- 2026-11-10: AI Forecast Cone (save kalibruojanti kainos ribų vėduoklė, online kvantiliai). 4 AI krypties modeliai pranašumo neturėjo; ribos pataiko 80 % visose 19 rinkų, TradingView SPY 81 % / 50 %. `tradingview/ai/REZULTATAI.md`
- 2026-11-10: 5 žvakių + volume panašumo paieška (6-os žvakės spėjimas), 25 rinkos/rėmai (1d, 1h, 5m): atspėja kryptį 50,7 % (monetos metimas). `tradingview/ai/pattern5.py`
- 2026-11-10: Box Breakout POC (ramios dėžės + POC + Fibonacci, `tradingview/Box_Breakout_POC.pine`). 12 rinkų 1d 2005–26: lūžis aukštyn su POC viršuje +0,37R/sandorį abiem laikotarpiais; žemyn −0,38R; kripto 15m/1h nuostolinga, apgaulingo lūžio strategija −0,4…−1R. TradingView dar nepatikrinta. `tradingview/ai/boxes.py`
- 2026-11-10: Box Breakout POC v2: dėžės nepersidengia, signalas tik iš ≥ 20 žvakių dėžių (+0,58R/sandorį, abiem laikotarpiais; 12 ž. +0,34R), nesignalinės dėžės paslepiamos.
- 2026-11-10: batch50e baigta pilnai (100 testų: 91 pavyko, 9 klaidų). Geriausia lieka ClucHAnix_5m alts10 +16,4 %/m. (kritimas 22 %), CombinedBinHAndClucV3 +15,3 %/m. (31 %). Naujų atrinktų nėra. `results/batch50e_results.csv`
- 2026-11-10: paleista batch50f (50 strategijų iš `extra/`, B–G; `make_batch.py` sudaro kitą partiją). 3m ir 30m duomenys sudaryti iš 1m ir 5m.
- 2026-11-11: batch50f baigta (B–G, 100 testų). Geriausia CombinedBinHAndClucV5Hyperoptable alts10 +10,8 %/m. (kritimas 13 %), ClucHAnix_BB_RPB_MOD btc_eth +8,4 %/m. (8 %). Naujų atrinktų (≥14 %/m.) nėra.
- 2026-11-11: Docker vaizdui pridėta `scikit-optimize` (skopt); perpaleisti 6 ankstesnių partijų testai, dėl jo nepasileidę – nieko naujo. 1m strategijos ant 10 altcoin'ų netelpa net į 10 GB (5 m. 1m duomenų), 26 tokie testai praleisti; jų BTC+ETH rezultatai silpni (≤ +4,4 %/m.). `freqtrade/rerun.sh` perpaleidžia klaidas (`MEM=10g`).
- 2026-11-11: batch50g baigta (G–N, 100 testų: 89 pavyko). NOTankAi_15_Cleaned* ir LookaheadStrategy – akivaizdus ateities duomenų naudojimas (+400…1200 %/m.), praleista.
- 2026-11-11: **NASOSv5_mod3 atrinkta** (alts10): +18,3 %/m., kritimas 3,3 %, kasmet pliuse; lookahead 0/20, recursive švari; nematytas 2018–21 +89 %/m., kritimas 21 %. Ichimoku_v37 (BTC+ETH 4h, +15,9 %/m.) švari, bet 2022–24 minuse – tik rizikingų sąraše. Skriptai `freqtrade/validate_g.sh`, `freqtrade/oos_batch.py`.
- 2026-11-11: NY pirmos 5m žvakės strategija NAS100 (vartotojo idėja), 2023-11 – 2026-11: geriausia (didelė žvakė, TP 2R) +4,6 %/m., kritimas 23 % vs laikant +22 %/m.; kitos versijos minuse. `tradingview/ny_first5/REZULTATAI.md`
- 2026-11-11: NowoIchimoku1hV2 (batch50h) 1h testas +35 %/m., lookahead/recursive švari, 2018–21 +72 %/m., bet su `--timeframe-detail 5m` tik +6,5 %/m. (alts10) ir +10,9 %/m. (BTC+ETH) – atmesta. Visos strategijos vienoje lentelėje: `results/VISOS_STRATEGIJOS.md`.
- 2026-11-11: batch50h baigta (87/100). Rsiqui_protections – atmestos Rsiqui kopija (np.gradient), SMAOffset alts10 +17 %/m., bet kritimas 33 %, 2022 minuse. Naujų atrinktų nėra.
- 2026-11-11: batch50i (75/100) ir batch50j (22/38) baigtos. TheForce (15m) +89…362 %/m., išlaiko 1m detalumą, bet vid. sandoris +0,04 %: su 0,15 % mokesčiu −55 %/m. – atmesta. Kitos silpnos (true_lambo +8 %/m.). `freqtrade/detail.sh` – testas su `--timeframe-detail`.
- 2026-11-11: atsisiųsti 11 GitHub repo (`sources_more/`, 179 strategijos) → batchM1–M4 (`make_batch_list.py`), eilė `freqtrade/queue.sh`. batchM1 vyksta: BB_RTR alts10 +12,4 %/m., kritimas 4 %.
- 2026-11-11: batchM1–M3 baigtos (37/31/6 ok, kitiems trūko modulių). Geriausios: BB_RTR alts10 +12,4 %/m., NFI5MOHO_WIP +11,2 %/m. – < 14 %. MomentumRegimeBasket (BTC+ETH +17 %/m.) naudoja ateities duomenis – atmesta. Pridėtas `docker_offline/custom_indicators.py`, 38 testai perpaleidžiami (`requeue.sh`).
- 2026-11-12: nauji 25 GitHub repo (`freqtrade/sources_more2`, 425 strategijos) → batchM5–M13 (`queue2.sh`). batchM5: nieko. batchM6: Ichimoku_v2 (4h) +17,3 %/m. ir Ichimoku_v16 (1d) +22,4 %/m. BTC+ETH – švarios, išlaikė 2018–21, bet kritimai 42–44 %, pelnas sutelktas 2024–25 → rizikingų sąraše. GodStraNew7 – ateities duomenys.
- 2026-11-12: batchM7: Ichimoku_v5 (alts10 4h) +17,1 %/m., kritimas 20/32 %, Ichimoku_v8 (BTC+ETH 4h) +15,1 %/m. – švarios, išlaikė 2018–21, bet nelygūs metai → rizikingų sąraše. EI3v2_tag_cofi_green_2 = EI3v2 kopija.
- 2026-11-12: **ckNSJT_morning atrinkta** (batchM8, alts10 5m): +21,2 %/m., lookahead 0/20, su 0,15 % mokesčiu +19 %/m., 2018–21 +90 %/m. (visi metai pliuse); 2022 −14 %, balanso kritimas 37 %.
- 2026-11-12: testai pristabdyti vartotojo prašymu batchM10 viduryje (36/100). Tęsti: `cd freqtrade && nohup ./queue2.sh` (baigti testai praleidžiami; batchM10–M13).
- 2026-11-12: testai tęsiami nuo batchM10 (`freqtrade/queue2.sh`, dabar M10–M13). Šioje kopijoje `.venv` → `~/trading/ft-venv` (tas pats freqtrade 2026.10). Vartotojo tikslas: ≥5 %/mėn.
- 2026-11-12: Instagram „nakties dėžės pusė“ (NQ) patikrinta: 81 %/75 % tiesa, bet prekiaujant pralaimi (−3,7 t./sandorį). Atmesta → `tradingview/ovn_box/REZULTATAI.md`
- 2026-11-12: Instagram „day-trader-skill“ (ORB akcijose) patikrinta ant 20 JAV akcijų 2021–26: −0,044 R/sandorį, kasmet minuse. Atmesta → `day-trader-skill/REZULTATAI.md`
- 2026-11-12: Instagram „8 trailing stop būdai“ (NQ) patikrinta: nė vienas nepagerina Noise Breakout (orig. +4,8 bp, geriausias trailing +1,8 bp), siauri stopai kenkia → `tradingview/trail_stops/REZULTATAI.md`
- 2026-11-12: Instagram „efektyvi riba“ (Markowitz) patikrinta su 12 ETF 2009–26: optimizavimas pagal praeitį nelenkia paprasto 60/40 → `efficient-frontier/REZULTATAI.md`
- 2026-11-12: Instagram „absorbcija“ (delta + volume) patikrinta ant BTC/ETH futures 5 min. 2021–26: filtras nieko neprideda prie paprasto atšokimo, su kaštais minuse → `absorption/REZULTATAI.md`
- 2026-11-12: Instagram „CE 50% Model“ (NQ) patikrinta 2016–26: veikia (+0,115 R, 10/11 m. pliuse, 2022–26 +17 %/m. prie 1 % rizikos, kritimas 25 %), žadėta 59 %/m. ne → `tradingview/ce50/REZULTATAI.md`
- 2026-11-12: CE50 tik long su 3x ETP: TQQQ (iki 16:00) +7,2 %/m., kritimas 35 %; QQQ3 (LSE, iki 11:30 ET) −0,9 %/m. Neverta.
- 2026-11-12: CE50 tik long NAS100 CFD 3x: +17,5 %/m. 2016–26, kritimas 29 %; 2022–26 +23,4 %/m.
- 2026-11-12: sukurtas TradingView skriptas `tradingview/CE50_NAS100.pine` (CE50 long, 3x, pranešimai)
- 2026-11-12: CE50 indikatoriaus versija `tradingview/CE50_NAS100_indikatorius.pine`
- 2026-11-12: CE50 Maven Omo 2-Step simuliacija 2025–26: tik long 1 % −27 $, long+short 1 % +1308 $, 2 % +4513 $ (Maven rodo „not available in your region“) → `tradingview/ce50/REZULTATAI.md`
- 2026-11-12: atrinktos strategijos per Maven 2025–26: max ~0,4 funded/mėn. (EI3v2 kripto, nepatikima), CE50 3 % 0,31/mėn.; 1/mėn. nepasiekia nė viena → `tradingview/ce50/REZULTATAI.md`
- 2026-11-12: Instagram „composite profilis“ (kestradess) patikrinta NAS100 2019–26: plonos/storos zonos greičio beveik nekeičia (20,2 vs 19,3 bp), prekyba −0,19 R. Atmesta → `tradingview/composite_profile/REZULTATAI.md`
- 2026-11-12: Instagram faiz.smc „GPT6 Astra prekiauja už mane (DeepCharts + GEX)“: tik vienas demo sandoris, jokių taisyklių, netestuojama. GEX reikia mokamų opcionų duomenų.
- 2026-11-12: Instagram „30 d. vidurkio taisyklė“ (nuo 1926) patikrinta: atsikartoja, bet pranašumas tik 1926–74; 2013–26 7,4 %/m. vs laikymas 14,9 %. Atmesta → `ma30_rule/REZULTATAI.md`
- 2026-11-12 16:15: queue2 (batchM10–M13) paleista iš naujo
- 2026-11-12: batchM10 tarpiniai: NOTankAi_vX/NOTankAi_5 (+869 %/m.) atmesta – argrelextrema per visą duomenų masyvą (ateities duomenys). lw_tdw_tdm_btc_eth_v1 (+75 %/m., 15m kalendoriaus dienos) atmesta – 2017–19 neveikia, o dienas renkant tik pagal praeitį (walk-forward 2020–26) pranašumo nėra; dienos pritaikytos prie istorijos (repo RoboticAutomations, 2026-05).
- 2026-11-12: batchM10 baigta. Peekaboo/V2/V4/V4002 (+28…+134 %/m., kritimas 0,5–3 %) atmesta – scipy find_peaks per visą masyvą (ateities duomenys). Kitų tinkamų nėra.
- 2026-11-12: batchM11 baigta. HurstCycleV6/HurstCycle7 (+289…+371 %/m.) atmesta – rolling(center=True) ir FFT per visą seriją (ateities duomenys).
- 2026-11-12: batchM12 baigta. grad (+54 %/m., kritimas 3,5 %) atmesta – np.gradient naudoja kitą žvakę (ateities duomenys).
- 2026-11-13: perskaityti 16 DMC (Dumb Money Hunter) YouTube video transkriptai, strategija aprašyta → `dmc/STRATEGIJA.md`
- 2026-11-13: sukurtas DMC TradingView indikatorius `tradingview/DMC_indikatorius.pine` (M/W/D/4H/1H kūnų lygiai, failure-to-gain/lose BUY/SELL, TP/SL linijos, pranešimai; nepatikrintas istorijoje)
- 2026-11-13: DMC indikatorius: spalvos (M mėlyna, W geltona, D balta), artimų lygių sujungimas, didesni užrašai, žalia/raudona linija = laukiamas BUY/SELL
- 2026-11-13: DMC indikatoriaus logika ištestuota NAS100 2016–26 (5/15 min., su/be filtro, long/short): visi variantai −0,09…−0,15 R/sandorį, nuostolinga → `dmc/REZULTATAI.md`
- 2026-11-13: `tradingview/DMC_lygiai.pine` – tik M/W/D kūnų lygiai, be užrašų ir signalų
- 2026-11-13: Trend Konsensusas + mėnesio/savaitės lygiai → `tradingview/Trend_Konsensusas_lygiai.pine`
- 2026-11-13: Collective2 gyvų sistemų peržiūra: 12 iš 261 (≥3 m.) atitinka ≥15 %/m. ir kritimą ≤30 %; išsiskiria ares (32 %/m., DD 14 %, 6,2 m.) → `live-track-records/collective2.md`
- 2026-11-13: Darwinex reikalauja prisijungimo; Myfxbook sąrašas – didelės rizikos forex/grid sistemos, neanalizuota.
- 2026-11-13: svertas 2x/3x/5x: EI3v2 3x +107 %/m. (kritimas 29 %), NASOSv5_mod3 5x +87 %/m. (28 %), ckNSJT netinka → `freqtrade/results/lev2/REZULTATAI.md`
- 2026-11-13: copy trading: Bybit nepasiekiamas (demo režimas); Binance 10 lyderių ≥2 m. su kritimu ≤30 %, išsiskiria MoneyBoxTM (+90 %/365 d., kritimas 16 %, kopijuotojai +47k $) → `live-track-records/copy_trading.md`
- 2026-11-13: Quantpedia 10 strategijų (kalendoriaus efektai, SPY/TLT, nafta, trendas 8 ETF, BTC valandos, BTC/ETH perbalansavimas): nė viena nelenkia SPY 2016–26 → `quantpedia/REZULTATAI.md`
- 2026-11-13: sources_more3 89 strategijos → batchM14 (50), batchM15 (39), paleista `freqtrade/queue3.sh` (Docker be interneto)
- 2026-11-13: batchM14–M15 baigtos (178 testai): tinkamų nėra; IchiV1_Optimizable (+776 %/m.) atmesta – lookahead bias (`results/validation/IchiV1_Optimizable_batchM14.log`). Visa eilė → `results/EIGA.md`
- 2026-11-13: svertas su 2020–21: EI3v2 3x kritimas 94 %, NASOSv5 5x bankrotas 2021; saugu tik 1x (EI3v2 +81 %/m., kritimas 17 %; NASOSv5 +37 %/m., 30 %), EI3v2 2x ant ribos (49 %). Auksas/NAS100/S&P – neveikia → `freqtrade/results/lev3/REZULTATAI.md`
- 2026-11-13: EI3v2 2,2x/2,4x/2,5x (alts10 2020–26): 2,4x +267 %/m., kritimas 49,6 %; 2,5x jau 60 % → riba
- 2026-11-13: savaitgalio testai: 141 naujas GitHub repo (`freqtrade/sources_more4`), 353 strategijos → batchM16–M23, paleista `freqtrade/queue4.sh` (Docker be interneto). Bybit demo botas paleistas iš naujo po perkrovimo (0 sandorių – atitinka backtestą, nuo 10-20 signalų nebuvo).
- 2026-11-13: savaitgalio planas: kas 2 val. patikra (botas, queue4, straipsniai `papers/EILE.md`), kas 8 val. naujienos `results/SAVAITGALIS.md` į GitHub
- 2026-11-13: straipsniai 1, 2, 5 (kripto momentum, atšokimas, mažos monetos): visos Binance USDT poros su išregistruotomis (700), `papers/xsec.py` – vyksta
- 2026-11-13: batchM16–M17 baigtos. FakeoutStrategy (+26 %/m., kritimas 0,1 %) atmesta – argrelextrema per visą masyvą; Precognition (+800 %/m.) atmesta – shift(-8), tiesiogiai žiūri į ateitį. Kitų tinkamų nėra.
- 2026-11-13: straipsniai 1, 2, 5 atmesti: 2018–21 momentum long-short +29 %/m., bet 2022–26 visi variantai minuse (−15…−85 %/m.) → `papers/01_kripto_momentum/REZULTATAI.md`
- 2026-11-13: straipsniai 3, 4 (funding carry, cash-and-carry): siunčiama funding istorija 659 kontraktams, `papers/carry.py` paleis automatiškai
- 2026-11-13: straipsnis 6 (TSMOM, 25 ETF, Moskowitz ir kt. 2012) atmestas: 2016–26 long-short 2x −1,0 %/m. (kritimas 35 %), long-only 1x +3,6 %/m. vs SPY +14,7 % → `papers/06_tsmom/REZULTATAI.md`
- 2026-11-13: straipsnis 10 (kripto valandų/dienų sezoniškumas, walk-forward, 8 monetos) atmestas: valandų efektas +1–2 bp/val., mokesčiai 20 bp suvalgo; dienų versija nelenkia laikymo → `papers/10_sezoniskumas/REZULTATAI.md`
- 2026-11-13: straipsnis 7 (žemas volatilumas / BAB, S&P 500 su istorine sudėtimi) atmestas: 2014–26 +10,8 %/m. vs SPY +13,5 %, kritimas toks pat (35 %); BAB +2,5 %/m.; realūs USMV/SPLV patvirtina → `papers/07_lowvol/REZULTATAI.md`
- 2026-11-13: straipsnis 9 (kripto porų prekyba, kointegracija/atstumas, 1h ir 5m) atmestas: nuostolinga net be mokesčių (−1…−17 %/m.), su 0,1 % −15…−91 %/m. → `papers/09_poros/REZULTATAI.md`
- 2026-11-13: straipsnis 8 (PEAD, S&P 500, 35,9 tūkst. Yahoo anonsų 2002–26) atmestas: long top 20 % +12,2 %/m. = lygiavertis krepšelis (+12,4 %), long-short +1,7 %/m. → `papers/08_pead/REZULTATAI.md`
- 2026-11-13: straipsnis 11 (pre-FOMC dreifas, 264 sprendimai 1994–2026) atmestas: iki 2011 +0,24 %/įvykį (t 2,3), 2012–26 +0,02 % (t 0,2) → `papers/11_fomc/REZULTATAI.md`
- 2026-11-13: straipsnis 12 (52 sav. maksimumo momentum, S&P 500) atmestas: 2014–26 long +10,5 %/m. vs lygiavertis +12,4 %, long-short −1,3 %/m. → `papers/12_52wh/REZULTATAI.md`
- 2026-11-13: straipsnis 13 (volatilumu valdomas portfelis, Moreira-Muir 2017): QQQ tikslinis 15 % vol ≤2x 2016–26 +17,7 %/m., kritimas 21 % (laikymas +19,1 %, 35 %), 1994–2015 +9,1 % vs +5,4 %; rizikos mažinimas, ne pelnas → `papers/13_volmanaged/REZULTATAI.md`
- 2026-11-13: straipsnis 14 (Heston-Sadka mėnesio sezoniškumas, S&P 500) atmestas: 2014–26 long top 10 % +10,3 %/m. vs lygiavertis 12,4 %, long-short −3,3 % → `papers/14_seasonality/REZULTATAI.md`
- 2026-11-13: queue4 (batchM16–M23) baigta. esv9_1h_v6 (+58…+209 %/m., kritimas 3–4 %) atmesta – perrašo kainas Heikin-Ashi reikšmėmis; pataisius (tikros kainos) −18…−28 %/m.
- 2026-11-13: **MACDVStrategy atrinkta** (nr. 5, BTC+ETH 1d): +16 %/m., kritimas 15 %; nematytas 2018–21 +73 %/m., kritimas 12 %; lookahead 0/20.
- 2026-11-13: straipsniai 3, 4: funding carry kas d. 2022–26 +17 %/m., bet kritimas 53 % ir 2024 −26 %; cash-and-carry BTC+ETH 2022–26 tik +3 %/m. (mažiau nei indėlis); daugiau monetų – minuse. Atmesta → `papers/03_funding_carry/REZULTATAI.md`
- 2026-11-13: NASOSv5_mod3 su 1m detalumu (alts10, 2022–25 po metus): 2022 +26,4 % (be detalumo +27,9), 2023 +8,5 (+8,7), 2024 +15,6 (+16,5), 2025 +56,9 (+27,3) – išlaikė
- 2026-11-13: MACDVStrategy su 5m detalumu (BTC+ETH 2021–26): +15,7 %/m. (be detalumo +16,0 %), kritimas 21 % – išlaikė
- 2026-11-13: straipsnis 17 (liekamasis momentum, FF3, S&P 500) atmestas: 2014–26 +13,8 %/m. = SPY (13,7 %), kritimas 39 % → `papers/17_resmom/REZULTATAI.md`
- 2026-11-13: straipsnis 18 (Jesse klasika): Dual Thrust BTC+ETH 1d +11,9 %/m., kritimas 11 %, kasmet pliuse 2018–26, 5m vykdymas patvirtina, bet su 0,15 % mokesčiu +7,5 %; Turtle BTC+ETH +14 %/m., kritimas 30–37 % → abu į rizikingų sąrašą, `papers/18_turtle/REZULTATAI.md`
- 2026-11-13 20:44: laiškas apie MACDVStrategy išsiųstas (Gmail)
- 2026-11-13: sources_more5 (56 repo, 172 strategijos) → batchM24–M27, paleista `freqtrade/queue5.sh`. Straipsnius (papers/) tuo pačiu metu tęsia kitas seansas.
- 2026-11-13: Dual Thrust ant Binance perp BTC/ETH (long, 0,05 %, su funding): 2021-11–26 +13,8 %/m., kritimas 12 %, kasmet pliuse 2020–26; long+short +5,6 %/m. → `papers/18_turtle/REZULTATAI.md`
- 2026-11-13: straipsniai 15–16 (kripto žemas vol / MAX long-short) atmesti: spot kainomis 2022–26 +85 %/m., bet su tikrais perp ir funding −8,5 %/m., kritimas 80 % (shortų funding ~35 %/m.); 2018–21 minuse → `papers/15_kripto_lowvol/REZULTATAI.md`
- 2026-11-13: straipsnis 19 (Larry Williams VB kripto) atmestas: 2021–26 BTC+ETH −9 %/m. (k=0,5); 20 (R-Breaker BTC/ETH 1h): tik trendas long +15,2 %/m. su 0,05 % (0,1 %: +10,5), kritimas 13 %, koreliacija su Dual Thrust 0,76 → į potencialių sąrašą
- 2026-11-13: straipsnis 21 (Pruitt/Hill trendo sistemos kripto 1d): Aberration BTC+ETH +17,8 %/m., kritimas 27 %, 2018–21 +88 %/m. → rizikingų sąrašas; King Keltner +16,7 % (38 %), kitos silpnesnės
- 2026-11-13: 22 (paprasti trendo filtrai kripto: Faber, 50/200, SMA200) atmesti: 2021–26 BTC+ETH −4…+13 %/m., kritimai 36–65 %
- 2026-11-13: Dual Thrust perrašyta į freqtrade (`user_data/strategies/papers/DualThrust.py`, 5m): BTC+ETH 2021–26 +11,7 %/m., kritimas 11,5 %, 408 sandoriai, lookahead 0/20 – atitinka pandas testą
- 2026-11-13: **Aberration atrinkta** (nr. 6, BTC+ETH 1d): freqtrade +18,4 %/m., kritimas 28 %, 40 sandorių, lookahead 0/20; nematytas 2018–21 +88 %/m. → `best_strategies/ATRINKTI_BOTAI.md`
- 2026-11-13: 23 (Darvas, Raschke Holy Grail/Turtle Soup, PSAR, Alligator, Seykota kripto 1d) atmesti: 2021–26 BTC+ETH −19…+7 %/m.
- 2026-11-13: Aberration parametrų jautrumas: 2021–26 +1,6…+24,7 %/m. (mediana ~12 %), 35/2 virš vidurkio
- 2026-11-13: 24 (BTC Mayer daugiklis, Pi Cycle, 200W) atmesti: signalai reti, kritimai 53–83 %

## 2026-11-13 – 1m detalumo patikra: ckNSJT_morning, EI3v2
- ckNSJT_morning alts10 (none → 1m): 2022 −9,5 → −0,3; 2023 29,2 → 31,2; 2024 88,8 → 85,3; 2025 20,4 → 31,1. ✅ išlaiko.
- EI3v2_tag_cofi_green alts10: 2022 15,4 → 5,5; 2023 27,4 → 25,9; 2024 54,1 → 43,9; 2025 15,8 → 11,8. ⚠️ ~¼ mažiau, bet kasmet pliuse.
- E0V1E_DCA3 nepavyko (market orderiai), perleista su `config_spot_market.json` (`freqtrade/detail_q4.sh`).

## 2026-11-13 – straipsniai 25–26
- #25 Connors RSI(2)/ConnorsRSI kripto 1d ❌ (BTC+ETH ≤ +11,7 %/m., 2018–21 ~0; alts10 po 2021 ~0) → `papers/25_connors/`.
- #26 Dienos vidaus momentum kripto 1h ❌ (koreliacija 0,11, bet mokesčiai suvalgo) → `papers/26_intraday_mom/`.
- #27 KAMA/Supertrend/HMA/Chandelier kripto 1d ❌ → `papers/27_trend3/`.
- #28 Mėnesio sandūros efektas ETF/kripto ❌ → `papers/28_tom/`.
- #29 Crabel NR4/NR7 kripto ❌ (pirma versija turėjo ateities info short pusėje, ištaisyta) → `papers/29_crabel/`.
- #30 Nakties grąžos ETF ❌ (kaštai suvalgo) → `papers/30_overnight/`.
- #31 BTC CME gap ❌ → `papers/31_cme_gap/`.
- #32 Funding kontrarinis BTC+ETH ⚠️ (+26 %/m., kritimas 30 %, bet alts neveikia) → `papers/32_funding_timing/`, įrašyta į rizikingų sąrašą.
- E0V1E_DCA3 1m detalumas (none → 1m): 2022 24,1 → 12,2; 2023 9,4 → 11,7; 2024 30,4 → 22,9; 2025 11,5 → 2,1. ⚠️ ~⅓ mažiau, realiai ~12 %/m. (Bybit demo botas su 15x – rezultatus vertinti atsargiai).
- #33 BTC/altų rotacija ❌ → `papers/33_altseason/`.
- FundingContrarian freqtrade: +26,5 %/m., kritimas 21,9 %, lookahead 0/20 signalų; +1 d. vėlavimas → +15,6 %. 2025–26 silpsta.
