# NY pirmos 5 min. žvakės strategija, NAS100 (vartotojo idėja, 2026-11-11)

Taisyklės: 09:30–09:35 NY žvakė žalia → pirkti jos uždaryme, raudona → parduoti. SL = žvakės atidarymas (rizika = kūnas, 1R).
Jei kūnas „labai mažas“ (< K × 20 d. pirmų žvakių kūno medianos), imama 2-a žvakė; jei ir ji maža – tą dieną nieko.
TP: 1R / 2R kainos tikslas arba išėjimas po 1 / 2 žvakių (T1/T2). Neuždaryta – 16:00. Kaštai 1,5 punkto/sandoriui.
Duomenys: Dukascopy 1m, 2023-11-10 – 2026-11-10 (741 diena). Rizika 1 % balanso sandoriui. Kodas `test.py`, visos versijos `results.csv`.

| Versija | Sandoriai | Laimi % | Vid. R | %/m. (1 % rizika) | Max kritimas |
|---|---|---|---|---|---|
| K=0,1 TP 1R | 734 | 48 | −0,12 | −26 | 61 % |
| K=0,25 TP 1R | 725 | 49 | −0,07 | −18 | 48 % |
| K=0,25 TP 2R | 725 | 36 | −0,01 | −4 | 30 % |
| K=0,5 TP 1R | 670 | 52 | −0,02 | −5 | 31 % |
| **K=0,5 TP 2R** | 670 | 37 | +0,03 | **+4,6** | 23 % |
| K=0,5 po 2 žvakių | 670 | 42 | −0,01 | −3,5 | 37 % |

NAS100 laikant: +22,3 %/m.

Išvados:
- Kryptis pagal pirmą žvakę beveik neturi pranašumo: be kaštų geriausia versija (K=0,5, 2R) +16,6 %/m., su 1,5 p. kaštais tik +4,6 %/m.
- Pirmos žvakės kūno mediana ~30 p., todėl SL mažas, o spread'as suvalgo didelę R dalį. Mažesnės žvakės (K 0,1–0,25) – aiškiai nuostolingos.
- 1R tikslas visada minuse; 2R šiek tiek geriau. 2024 m. silpniausi.
- Nelenkia laikymo; nerekomenduojama. Nebent brokeris su < 0,5 p. kaštais – tada verta tikrinti TradingView su K=0,5 ir 2R.
