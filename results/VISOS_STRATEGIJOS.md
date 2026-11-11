# Visos vertos dėmesio strategijos (2026-11-11)

Kripto: Binance, 2021-11-08 – 2026-11-08, 0,1 % mokestis (futures 0,05 %), 1000 USDT. 2021* = nuo lapkr. 8, 2026* = iki lapkr. 8.
„alts10“ = XRP, BNB, SOL, DOGE, ADA, TRX, LINK, AVAX, LTC, DOT. Svertas 1x = be sverto (spot).

## Kripto botai (Freqtrade)

| Strategija | Rinka | Svertas | %/m. | 2021* | 2022 | 2023 | 2024 | 2025 | 2026* | Max kritimas | Nematytas 2018–21 | Būsena |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| NowoIchimoku1hV2 | alts10, 1h | 1x | 35,4 → **6,5** su 5m detalumu | +3,4 | +55,1 | +50,3 | +79,4 | +6,7 | −1,4 | 16,7 % (5m det.: 28,6 %) | +71,7 %/m., krit. 8,6 % | ❌ 1h rezultatas išpūstas |
| NowoIchimoku1hV2 | BTC+ETH, 1h | 1x | 31,9 → **10,9** su 5m detalumu | −4,0 | +67,9 | +19,0 | +59,8 | +20,4 | +8,1 | 12,7 % (5m det.: 20,7 %) | +43,5 %/m., krit. 20,7 % | ❌ 1h rezultatas išpūstas |
| EI3v2_tag_cofi_green | alts10, 5m | 1x | 25,1 | +7,3 | +15,4 | +27,4 | +54,5 | +16,4 | +8,2 | 14,9 % | +71 %/m., krit. 17 % | ✅ atrinkta |
| EI3v2 + E0V1E_DCA3 po 50 % | alts10, 5m | 1x | 21,3 | – | +20 | +18 | +43 | +14 | +6 | 6,4 % | +70,5 %/m., krit. 7,8 % | ✅ atrinkta |
| NASOSv5_mod3 | alts10, 5m | 1x | 18,3 | +6,3 | +29,4 | +8,7 | +16,6 | +27,3 | +4,1 | 3,3 % | +89 %/m., krit. 21 % | ✅ atrinkta |
| E0V1E_DCA3 | alts10, 5m | 1x | 17,1 | +7,6 | +24,1 | +9,4 | +30,5 | +11,4 | +3,7 | 6,5 % | +70 %/m., krit. 5 % | ✅ atrinkta |
| Ichimoku_v37 | BTC+ETH, 4h | 1x | 15,9 | −3,7 | −6,6 | −7,5 | +57,3 | +53,7 | +3,9 | 16,1 % | +89 %/m., krit. 22 % | ⚠️ 3 metai minuse |
| E0V1E_DCA3 futures | alts10, 5m | 2x | 18,3 | – | – | – | – | −42 | – | 55,7 % | – | ❌ likvidacijos 2025-10-10 |
| E0V1E_DCA3 futures | alts10, 5m | 3x | 41,7 | – | – | – | – | −30 | – | 51,6 % | – | ⚠️ likvidacijos |
| E0V1E_DCA3 futures | alts10, 5m | 5x | 60,1 | – | – | – | – | −32 | – | 57,4 % | – | ⚠️ likvidacijos |
| E0V1E_DCA3 futures | alts10, 5m | 10x | 53,4 | – | – | – | – | −17 | – | 70,7 % | – | ⚠️ 2 likvidacijos, 1-as mėn. −32 % |
| E0V1E_DCA3 futures (Bybit demo) | alts10, 5m | 15x | netestuota | | | | | | | > 70 % tikėtina | – | paleistas demo 2026-11-10 |
| VolatilitySystem | BTC+ETH futures, 1h | 2x | 69,8 | +7,2 | +308,5 | +126,8 | +14,5 | +24,3 | −0,2 | 53,4 % | – | ⚠️ be stop-loss |
| Laikyti alts10 | | 1x | −9 | | | | | | | ~80 % | | palyginimui |
| Laikyti BTC+ETH | | 1x | −4 | | | | | | | ~65 % | | palyginimui |

## Akcijos / indeksai

| Strategija | Rinka | Svertas | %/m. | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | Max kritimas | Laikotarpis | Būsena |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Noise Breakout | NAS100, intraday | 1x | 15,0 (2021–24), 7,7 (2025–26) | +8,8 | +25,4 | +15,3 | +8,2 | +6,6 | +5,0 | 6,5 % | 2021–26 | ✅ TradingView įrankis (metai – 30 min. versijos) |
| Swing Trend Pullback | 19 rinkų, 1d | 1x | 10,4 | – | – | – | – | – | – | 32 % | 2015–26 | mažesnis kritimas nei laikant (41 %) |
| LAA | ETF | 1x | 9,7 | – | −14 | – | – | – | – | 20 % | 2008–26 | saugus, < SPY |
| HAA | ETF | 1x | 9,0 | – | +3 | – | – | – | – | 13 % | 2008–26 | saugus, < SPY |
| BAA-G12 | ETF | 1x | 8,1 | – | 0 | – | – | – | – | 14 % | 2008–26 | saugus, < SPY |
| Permanent Portfolio | ETF | 1x | 6,7 | – | −14 | – | – | – | – | 18 % | 2008–26 | saugus, < SPY |
| TQQQ kai QQQ > 200 d. | ETF | 3x | 24,5 | – | −44 | – | – | – | – | 61 % | 2008–26 | ⚠️ 2000–10 būtų −90 % |
| EI3v2 ant 3x ETF | 18 sint. 3x ETF, 1d | 3x | 13,5 | – | – | – | – | – | – | 14,5 % | 2021–26 | < 14 % riba |
| Laikyti SPY | | 1x | 12,0 | | −18 | | | | | 47 % | 2008–26 | palyginimui |
| Laikyti QQQ | | 1x | 16,6 | | −33 | | | | | 47 % | 2008–26 | palyginimui |

Pastaba: 1h ir ilgesnių žvakių strategijas būtina tikrinti su `--timeframe-detail 5m` (trailing stop / ROI žvakės viduje). NowoIchimoku1hV2 nukrito nuo 35 → 6,5 %/m.
