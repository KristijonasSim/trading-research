# 50 naujų Freqtrade strategijų (2026-11-09)

2021-11-08 – 2026-11-08 (5 m.), Binance spot, 0,1 % mokestis, 1000 USDT. Grupės: BTC+ETH ir top 10 altcoin'ų.
Paleista Docker konteineryje be interneto (`freqtrade/run_batch.py`). Pilni rezultatai: `batch50_results.csv`.
Iš 100 testų: 86 pavyko, 14 nepasileido (7 strategijos su kodo klaidomis).

## Tik > 5 %/m.
| Strategija | Rinka | Rėmas | %/m | Vid. metų % | Iš viso | Max kritimas | Sandorių/m | Laimi % | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | Patikra |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EI3v2_tag_cofi_green | altcoin'ai | 5m | **25,1** | 21,5 | +207 % | 14,9 % | 368 | 93,5 | 7,3 | 15,4 | 27,4 | 54,5 | 16,4 | 8,2 | ✅ švari (su 1m detalumu ~¼ mažiau) |
| E0V1E_DCA3 | altcoin'ai | 5m | **17,1** | 14,5 | +120 % | 6,5 % | 215 | 86,5 | 7,6 | 24,1 | 9,4 | 30,5 | 11,4 | 3,7 | ✅ švari |
| ActionZone | altcoin'ai | 1d | 12,8 | 20,3 | +83 % | 49,3 % | 86 | 24,5 | −8,5 | −36,6 | 14,0 | 137,0 | 1,4 | 14,7 | ✅ švari, bet didelis kritimas |
| CombinedBinHAndCluc2021 | altcoin'ai | 5m | 10,4 | 9,2 | +64 % | 21,1 % | 369 | 64,7 | −4,0 | 9,5 | 28,8 | 17,0 | −5,7 | 9,6 | ✅ švari |
| E0V1E | altcoin'ai | 5m | 7,7 | 6,6 | +45 % | 1,9 % | 28 | 80,0 | 2,6 | 12,5 | 3,5 | 16,8 | 3,3 | 0,7 | ⚪ per mažai sandorių patikrai |
| BigTrader | altcoin'ai | 5m | 5,9 | 5,0 | +33 % | 0,0 % | 20 | 100 | 2,1 | 6,3 | 4,2 | 10,5 | 6,1 | 0,5 | ⚪ per mažai sandorių patikrai |
| ElliotV5_SMA | altcoin'ai | 5m | 5,3 | 4,5 | +30 % | 3,2 % | 56 | 72,4 | −1,2 | 15,2 | 5,2 | 6,8 | 2,7 | −1,4 | ✅ švari |
| ~~ichiV1~~ | abi | 5m | ~~117–498~~ | | | | | | | | | | | | ❌ netikra: perka Heikin-Ashi kainomis + žiūri į ateitį. Ištaisyta: −58,6 % |

Altcoin'ų „pirkti ir laikyti“ per tą patį laikotarpį: 1000 → 620 (−9 %/m.).
