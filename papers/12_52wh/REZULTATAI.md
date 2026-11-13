# #12 52 savaičių maksimumo momentum (George, Hwang 2004) – ❌ atmesta

S&P 500 akcijos (tik tuo metu indekse, duomenys kaip #7), kas mėnesį reitingas pagal kaina / 52 sav. maksimumas, 6 persidengiančios kohortos, mokestis 0,1 %. Skriptas `test.py`, lentelė `REZULTATAI.txt`.

| Variantas | 2002–13 %/m. (kritimas) | 2014–26 %/m. (kritimas) | Sharpe 14–26 |
|---|---|---|---|
| Long arčiausiai maksimumo 10 %, 6 mėn. | +8,1 (49 %) | +10,5 (37 %) | 0,70 |
| Long-short 30 %, 6 mėn. | −5,0 (55 %) | −1,3 (26 %) | −0,16 |
| 12-1 momentum long 10 % (palyginimui) | +9,6 (59 %) | +13,5 (36 %) | 0,69 |
| Visos akcijos lygiaverčiai | +13,2 (55 %) | +12,4 (40 %) | 0,75 |
| SPY | +6,1 (55 %) | +13,5 (34 %) | 0,82 |

- S&P 500 akcijose 52 sav. maksimumo efekto nėra nė viename laikotarpyje: long tik atsilieka nuo lygiaverčio krepšelio, long-short neigiamas.
- Ribotumas: trūksta dalies iš indekso išėjusių akcijų (bankrotų), todėl short pusė gali atrodyti blogiau nei realiai. Bet ir long pusė pranašumo neturi.
