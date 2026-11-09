# Antra 50 Freqtrade strategijų partija (2026-11-09)

Tos pačios sąlygos kaip `batch50_ranking.md` (5 m., Binance spot, 0,1 %, 1000 USDT, Docker be interneto).
100 testų: 78 pavyko, 22 nepasileido (kodo klaidos / numpy 2 nesuderinamumas). Pilni rezultatai: `batch50b_results.csv`.

## > 5 %/m.
| Strategija | Rinka | Rėmas | %/m | Max kritimas | Sandorių/m | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | Pastaba |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EMAPriceCrossoverWithThreshold | BTC+ETH | 1h | 21,4 | 23,9 % | 48 | – | −14,0 | 23,3 | 109,2 | 10,6 | 7,4 | ✅ švari, bet be 2024 tik ~6 %/m. – neatrinkta |
| AlligatorStrategy | altcoin'ai | 1h | 8,1 | 50,5 % | 333 | −2,1 | −11,1 | 53,4 | 93,1 | −30,0 | −18,2 | labai nestabili |
| BBRSIv2 | BTC+ETH | 15m | 8,0 | 28,2 % | 21 | 11,2 | 7,2 | – | 32,3 | 29,7 | −28,2 | |
| AlligatorStrategy | BTC+ETH | 1h | 6,6 | 32,3 % | 67 | −18,9 | −1,5 | 30,3 | 82,9 | −17,8 | −12,2 | |
| BigZ03 | altcoin'ai | 5m | 5,7 | 9,9 % | 108 | 2,9 | 10,9 | 8,7 | 4,1 | 12,8 | −9,5 | |
| ~~GodStraNew~~ | abi | 4h | 15,8–22,5 | | 0,4–1,8 | | | | | | | tik 2–9 sandoriai per 5 m. – nereikšminga |

Naujų atrinktų botų nėra.
