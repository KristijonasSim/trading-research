# #17 Liekamasis momentum (Blitz, Huij, Martens 2011) – ❌ atmesta

S&P 500 (tik tuo metu indekse), 36 mėn. regresija prieš Fama-French 3 faktorius (Ken French duomenys iki 2026-09), signalas = liekanų suma t−12..t−2 / std. Long top 10 %, mokestis 0,1 %. Skriptas `test.py`, lentelė `REZULTATAI.txt`.

| Variantas | 2003–13 %/m. (kritimas) | 2014–26 %/m. (kritimas) | Sharpe 14–26 |
|---|---|---|---|
| Liekamasis momentum, 1 mėn. | +12,5 (50 %) | +13,8 (39 %) | 0,77 |
| 12-1 momentum, 6 mėn. | +11,2 (60 %) | +14,7 (36 %) | 0,75 |
| Visos akcijos lygiaverčiai | +15,8 (55 %) | +12,0 (40 %) | 0,72 |
| SPY | +9,1 (55 %) | +13,7 (34 %) | 0,84 |

- Liekamasis momentum turi mažesnį kritimą nei paprastas momentum, bet SPY nelenkia nei grąža, nei Sharpe. Kaip ir anksčiau tikrintas S&P 500 momentum (`industry-trends/`).
