# #7 Žemo volatilumo / betting-against-beta S&P 500 (Frazzini, Pedersen 2014) – ❌ atmesta

Kas mėnesį iš tuo metu S&P 500 esančių akcijų (istorinė sudėtis fja05680/sp500, Yahoo kainos), mokestis 0,1 %. Skriptas `test.py`, pilna lentelė `REZULTATAI.txt`.

| Strategija | 2001–13 %/m. (kritimas) | 2014–26 %/m. (kritimas) | Sharpe 14–26 |
|---|---|---|---|
| Žemas vol, 100 akcijų | +9,0 (42 %) | +10,8 (35 %) | 0,79 |
| Žema beta, 100 akcijų | +12,8 (40 %) | +10,0 (34 %) | 0,75 |
| BAB long-short (svertas ≤ 2x) | +5,8 (31 %) | +2,5 (34 %) | 0,25 |
| Visos akcijos lygiaverčiai | +12,4 (55 %) | +12,4 (40 %) | 0,74 |
| SPY | +4,6 (55 %) | +13,5 (34 %) | 0,82 |
| **USMV – realus ETF** | – | +10,7 (33 %) | 0,81 |
| **SPLV – realus ETF** | – | +9,2 (36 %) | 0,67 |

- 2001–13 (straipsnio laikotarpis) efektas buvo: tokia pati grąža kaip SPY, bet mažesnis svyravimas.
- 2014–26 žemas volatilumas atsilieka nuo SPY 3 p. p. per metus, o kritimas toks pat (COVID 2020, palūkanų kilimas 2022–23). Tą patį rodo realūs ETF USMV ir SPLV, kuriais prekiaujama nuo 2011 m., tad tai ne testo klaida.
- BAB long-short po 2014 m. beveik nieko neuždirba (+2,5 %/m.).
- Ribotumas: iki 2011 m. Yahoo neturi 35–50 % iš indekso išėjusių akcijų, todėl lyginta ir su to paties rinkinio lygiaverčiu krepšeliu.
