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
