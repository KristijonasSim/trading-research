# 5 geriausios strategijos (2026-11-16)

Atrinkta iš 23 strategijų (`ATRINKTI_BOTAI.md`) pagal 5 dalykus:
- ar strategija išlaiko nematytą laikotarpį;
- ar išlaiko tikslesnį 1 min. testą;
- ar išlaiko patikrą su 2021 m. monetomis (įskaitant žlugusias LUNA, FTT);
- kokie kritimai;
- ar pliuse beveik kasmet.

| # | Strategija | Kur | %/m. 2021–26 | Kritimas | Kodėl gera |
|---|---|---|---|---|---|
| 1 | **EI3v2_tag_cofi_green_2_4** (nr. 19) | 10 altcoin'ų, 5m | +27 (futures su mokesčiais +24) | 5–9 % | Su 2021 m. monetomis net +36 %/m. Veikia ir futures rinkoje. Su 1 min. testu ~¼ mažiau. |
| 2 | **DS_Green_5m** (nr. 13) | 10 altcoin'ų, 5m | +26,6 | 6,7 % | Pliuse kasmet. Su 2021 m. monetomis +19,8 %/m. Su 1 min. testu ~¼ mažiau. |
| 3 | **NASOSv5_mod3** (nr. 3) | 10 altcoin'ų, 5m | +18,3 | 3,3 % | 1 min. testas rezultato nepablogina. 2018–21 +89 %/m. |
| 4 | **BearBull3** (nr. 16) | 10 altcoin'ų, 5m | +15,5 | 9,4 % | Pliuse kasmet. Su 2021 m. monetomis +15,3 %/m., kritimas tik 10 %. Stabiliausia. |
| 5 | **MACDVStrategy** (nr. 5) | BTC+ETH, 1d | +16,0 | 14,7 % | Kita rinka ir kitas stilius (lėtas trendas), todėl papildo kitas 4. 2018–21 +73 %/m. |

## Dabartinis Bybit demo botas (E0V1E_DCA3, 15x svertas)
- **Techniškai veikia gerai.** Pakartojau tas pačias dienas (nuo 11-10) teste su Bybit duomenimis: strategija taip pat neatidarė nė vieno sandorio. Botas nieko nepraleido.
- **Bet strategija 2026 m. prekiauja labai retai.** Nuo sausio Bybit duomenimis tik 46 sandoriai, paskutinis spalio 8 d. Kovo–gegužės nebuvo nė vieno.
- **2026 m. rezultatas su 15x svertu:** −9,4 %, didžiausias kritimas 22 %.
- Su tikslesniu 1 min. testu E0V1E_DCA3 duoda ~12 %/m. (be sverto), o tai mažiau už 14 %/m. ribą. Į 5 geriausių sąrašą ji nepateko.

## Siūlymas
- Pakeisti bote strategiją į **EI3v2_tag_cofi_green_Future_Long_3**:
  - tai nr. 1 strategija, jau paruošta futures rinkai;
  - be sverto, tie patys 10 altcoin'ų;
  - testuota su tikrais funding mokesčiais: +24 %/m., kritimas 4,6 %;
  - prekiauja ~1 kartą per dieną.
- Svertas: ne daugiau 2x. Anksčiau tikrinta, kad EI3v2 riba yra ~2,4x, o 3x nebeišlaiko 2020–21.
- Failas: `best_strategies/EI3v2_tag_cofi_green_Future_Long_3.py`.
- Keisti tik Krisui leidus (bote nustatymų nekeičiu be leidimo).
