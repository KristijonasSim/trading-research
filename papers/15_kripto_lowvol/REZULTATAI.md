# #15 Kripto žemo volatilumo anomalija (Burggraf, Rudolf 2021) ir #16 MAX efektas (Li ir kt. 2021) – ❌ atmesta

Top 50 Binance USDT porų pagal apyvartą (su išregistruotomis), kas savaitę, mokestis 0,1 %. Skriptai `test.py` (spot kainos), `age.py` (monetos amžius), `perp.py` (tikri perp kontraktai su funding).

**Spot kainomis (teorinis short):**

| Variantas | 2018–21 %/m. (kritimas) | 2022–26 %/m. (kritimas) |
|---|---|---|
| Žemas vol long-short | −7,7 (55 %) | +85,1 (22 %) |
| Mažas MAX long-short | −13,2 (54 %) | +72,2 (25 %) |
| Žemas vol tik long | +49,1 (80 %) | −15,9 (74 %) |
| BTC laikyti | +45,7 (72 %) | +7,8 (67 %) |

Pelnas kyla iš labai svyruojančių altcoin'ų shortinimo (jie 2022–26 krito −83 %/m.). Ne nauji listingai: išlieka ir su ≥ 2 m. monetomis. Duomenų klaidų nėra (LUNA, OM kritimai tikri).

**Su tikrais Binance perp kontraktais ir funding:**

| Variantas | 2020–21 %/m. | 2022–26 %/m. (kritimas) |
|---|---|---|
| Long-short top 50, 0,05 % | −23,1 | **−8,5 (80 %)** |
| Tas pats be funding | −22,6 | +26,1 (54 %) |
| Long-short top 100 | −22,7 | −3,6 (56 %) |
| Tik short aukšto vol | −94 | −41 (100 %) |

- Labai svyruojančių monetų shortai perpildyti: funding short pusei kainuoja ~35 %/m. ir suvalgo visą pelną. Be to, perp kainos svyruoja labiau nei spot (short squeeze'ai).
- 2018–21 strategija buvo minuse. Spot rezultatas buvo teorinis, nes taip shortinti neįmanoma.
