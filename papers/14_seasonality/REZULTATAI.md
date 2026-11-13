# #14 Akcijų sezoniškumas pagal kalendorinį mėnesį (Heston, Sadka 2008) – ❌ atmesta

S&P 500 (tik tuo metu indekse), signalas = vidutinė akcijos grąža tą patį mėnesį per ankstesnius 3–10 metų, mokestis 0,1 %. Skriptas `test.py`, lentelė `REZULTATAI.txt`.

| Variantas | 2004–13 %/m. (kritimas) | 2014–26 %/m. (kritimas) | Sharpe 14–26 |
|---|---|---|---|
| Long top 10 % | +18,5 (62 %) | +10,3 (43 %) | 0,58 |
| Long-short 10 % | −0,5 (19 %) | −3,3 (38 %) | −0,47 |
| Long blogiausi 10 % | +14,0 (63 %) | +12,4 (42 %) | 0,65 |
| Visos akcijos lygiaverčiai | +13,3 (55 %) | +12,4 (40 %) | 0,75 |
| SPY | +7,4 (55 %) | +13,5 (34 %) | 0,82 |

- 2004–13 long top atrodo gerai, bet long-short ≈ 0: tai buvo tik didesnės rizikos akcijos (kritimas 62 %), ne sezoniškumas.
- 2014–26 sezoniškai „geriausios“ akcijos uždirba mažiau nei „blogiausios“. Efekto S&P 500 nėra.
