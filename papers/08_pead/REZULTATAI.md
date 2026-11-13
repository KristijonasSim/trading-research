# #8 Pelno anonsų dreifas (PEAD) – ❌ atmesta

S&P 500 akcijos (tik tuo metu indekse), Yahoo pelno datos ir EPS staigmena, 35 881 anonsas 2002–2026 (625 akcijos). Įeinama reakcijos dienos uždarymu, laikoma 20 arba 60 prekybos dienų, mokestis 0,1 %. Skriptai `fetch.py`, `test.py`, pilna lentelė `REZULTATAI.txt`.

| Variantas | 2005–13 %/m. (kritimas) | 2014–26 %/m. (kritimas) | Sharpe 14–26 |
|---|---|---|---|
| Long top 20 % staigmenų, 60 d. | +12,8 (57 %) | +12,2 (42 %) | 0,70 |
| Long top 20 %, 20 d. | +11,3 (55 %) | +5,0 (46 %) | 0,34 |
| Long-short 20 %, 60 d. | +1,7 (11 %) | +1,7 (6 %) | 0,58 |
| Long blogiausi 20 %, 60 d. | +8,3 (67 %) | +8,4 (41 %) | 0,52 |
| Visos S&P akcijos lygiaverčiai | +12,5 (55 %) | +12,4 (40 %) | 0,75 |
| SPY | +7,0 (55 %) | +13,5 (34 %) | 0,82 |

- Efektas dar matomas: akcijos su geriausiomis staigmenomis per 60 d. uždirba ~4 p. p. per metus daugiau nei su blogiausiomis.
- Bet tik pirkimų versija neviršija paprasto visų S&P akcijų krepšelio, o long-short duoda tik +1,7 %/m.
- Didžioji reakcija įvyksta pirmąją dieną (atidarymo kainų neturime, pagauti jos nebandyta).
- Ribotumas: Yahoo anonsų datos tik ~700 akcijų, iš indekso išėjusių iki 2011 m. trūksta.
