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
