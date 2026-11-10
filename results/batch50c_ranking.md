# Trečia 50 Freqtrade strategijų partija (2026-11-10)

Tos pačios sąlygos kaip `batch50_ranking.md` (5 m., Binance spot, 0,1 %, 1000 USDT, Docker be interneto).
100 testų: 82 pavyko, 18 nepasileido (kodo klaidos). Pilni rezultatai: `batch50c_results.csv`.

## > 5 %/m.
| Strategija | Rinka | Rėmas | %/m | Max kritimas | Sandorių/m | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | Pastaba |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ~~NOTankAi_15~~ | abi | 15m | 478–884 | 0–3 % | 300–1500 | | | | | | | ❌ `argrelextrema` žiūri 5 žvakes į ateitį (100 % laimi) |
| ~~Rsiqui~~ | abi | 5m | 55–225 | 25–31 % | 980–5050 | | | | | | | ❌ `np.gradient` naudoja kitos žvakės RSI |
| PrawnstarOBV | altcoin'ai | 1h | 42,6 | 63,3 % | 1010 | −19,8 | −26,0 | 323,0 | 223,3 | −2,9 | −25,3 | 4 nuostolingi metai |
| PrawnstarOBV | BTC+ETH | 1h | 14,7 | 57,0 % | 108 | −22,0 | −49,2 | 156,4 | 109,0 | 13,5 | −17,9 | |
| MAC | BTC+ETH | 1d | 12,5 | 15,0 % | 1,6 | – | – | −15,0 | 21,2 | 87,1 | −6,4 | 8 sandoriai per 5 m. |
| NotAnotherSMAOffsetStrategy | altcoin'ai | 5m | 7,5 | 3,5 % | 75 | 2,7 | 6,3 | 14,7 | 12,3 | 2,5 | −0,4 | stabili, bet maža grąža |
| MAC | altcoin'ai | 1d | 6,9 | 11,0 % | 8 | – | −1,5 | −8,8 | 8,6 | 51,1 | −5,4 | |
| SampleStrategy | altcoin'ai | 5m | 5,3 | 2,9 % | 77 | 1,1 | 4,5 | 8,1 | 12,2 | −1,4 | 2,3 | |

Naujų atrinktų botų nėra.
