# #6 Laiko eilučių momentum (Moskowitz, Ooi, Pedersen 2012) – ❌ atmesta

25 ETF (akcijos, obligacijos, žaliavos, valiutos, NT), kas mėnesį: 12 mėn. grąža virš BIL → long (arba short), svoris = 40 % / ETF volatilumas / N, bendras svertas ribojamas 1x arba 2x. Mokestis 0,05 %, laisvi pinigai BIL. Skriptas `test.py`, pilna lentelė `REZULTATAI.txt`.

| Variantas | 2008–15 %/m. (kritimas) | 2016–26 %/m. (kritimas) |
|---|---|---|
| Long-only 1x | +2,2 (9 %) | +3,6 (13 %) |
| Long-only 2x | +4,1 (15 %) | +5,7 (18 %) |
| Long-short 2x (kaip straipsnyje) | +3,9 (25 %) | −1,0 (35 %) |
| Long-only 6 mėn. 1x | +4,0 (10 %) | +4,2 (9 %) |
| SPY | +6,5 (52 %) | +14,7 (34 %) |
| 60/40 | +6,2 (33 %) | +9,7 (22 %) |

Išvada: po paskelbimo long-short versija neuždirba (vienintelis geras metas – 2022 m. +10,6 %). Long-only turi mažus kritimus, bet grąža 2–3 kartus mažesnė nei 60/40. Lenkia tik 2022 m. kritimą, kaip ir anksčiau tikrintos LAA/HAA (`etf-rotation/`).
