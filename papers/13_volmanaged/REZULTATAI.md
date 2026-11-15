# #13 Volatilumu valdomas portfelis (Moreira, Muir 2017) – ⚠️ veikia kaip rizikos mažinimas, ne papildomas pelnas

Kas mėnesį indekso dalis = tikslinis volatilumas (15 %) / praeito mėnesio volatilumas (arba 1/dispersija kaip straipsnyje), apribota 1x/2x, likutis T-bill, skolinimas +1 %. Mokestis 0,05 %. Skriptas `test.py`, lentelė `REZULTATAI.txt`.

| Variantas | 1994–2015 %/m. (kritimas) | 2016–26 %/m. (kritimas) | 2021-11 – 2026-11 | Sharpe 16–26 |
|---|---|---|---|---|
| QQQ laikyti | +5,4 (83 %) | +19,1 (35 %) | +11,2 (35 %) | 0,89 |
| **QQQ tikslinis 15 % vol, ≤2x** | **+9,1 (39 %)** | +17,7 (**21 %**) | **+13,1 (20 %)** | 0,98 |
| QQQ tikslinis 15 % vol, ≤1x | +8,9 (39 %) | +15,6 (21 %) | +11,9 (20 %) | 1,00 |
| SPY laikyti | +8,9 (55 %) | +14,7 (34 %) | +11,0 (24 %) | 0,86 |
| SPY 1/dispersija, ≤1x (straipsnis) | +7,1 (20 %) | +9,7 (15 %) | – | 0,98 |

- Po paskelbimo (2016–26) veikia, kaip žadėta: grąža panaši į laikymą arba šiek tiek mažesnė, o kritimas ~40 % mažesnis. 2000–03 m. QQQ −21 %/m. → −2 %/m.
- Grąža laikymo nelenkia (išskyrus 5 m. langą), todėl į atrinktus (≥14 %/m.) nepatenka. Tai **rizikos valdymo taisyklė**, kurią galima uždėti ant QQQ/SPY pozicijos (QLD su svertu iki 2x).
- 1/dispersija (originali formulė) per daug sumažina poziciją po krizių, todėl praranda atšokimą (2020 m. −2 % vs SPY +18 %).

## Agresyvus variantas (2026-11-15, `lev.py`, `REZULTATAI_lev.txt`)
QQQ tikslinis volatilumas 30–45 %, iki 3–4x: 2010–19 +30…+43 %/m., 2020–26 +25…+35 %, **bet 1999–2009 −2…+4 %, kritimai 68–86 %**. Su SMA200 filtru 1999–2009 vis tiek ~0 (kritimai 46–69 %), o 2010–19 tik +18…+22 %. SPY silpniau. 40–50 %/m. tik geruose dešimtmečiuose.
