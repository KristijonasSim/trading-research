# #20 R-Breaker (BTC/ETH, 1h) – ⚠️ potenciali, ta pati idėja kaip Dual Thrust

Lygiai iš vakar H/L/C (iš valandos uždarymų), signalas valandos uždarymu, įvykdymas kitos valandos atidarymu, uždaroma 00 UTC. Skriptas `test.py`, lentelė `REZULTATAI.txt`.

| Variantas | Mokestis | 2018–2021-11 %/m. (kritimas) | 2021-11–2026-11 %/m. (kritimas) |
|---|---|---|---|
| Tik trendas (buy break), long | 0,05 % | +38,5 (9 %) | **+15,2 (13 %)** |
| Tik trendas, long | 0,1 % | +32,7 (10 %) | +10,5 (15 %) |
| Trendas + atšokimas, long+short (originalas) | 0,05 % | +56,9 (21 %) | +10,7 (22 %) |
| Trendas + atšokimas, long+short | 0,1 % | +42,4 (22 %) | −0,4 (28 %) |

- Tik trendo long versija: metai 2022 +26, 2023 +4, 2024 +32, 2025 +12, 2026 +3 % (0,05 %).
- Koreliacija su Dual Thrust (#18) 0,76; 50/50 derinys 2021–26 +13,7 %/m., kritimas 10 %. Tai ta pati „dienos pramušimo“ idėja.
- Atšokimo (reversal) dalis ir short kripto rinkoje kenkia. Labai jautri mokesčiui, todėl tinka tik futures / maker.
