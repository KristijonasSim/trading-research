# Atrinkti botai

Čia dedame tik tas strategijas, kurios praėjo visus testus. Kriterijus: **≥ 14 %/m.** per paskutinius 5 metus ir švari patikra (nežiūri į ateitį).

Testavimo sąlygos visiems: 2021-11-08 – 2026-11-08, Binance, 0,1 % mokestis, pradžia 1000 USDT.
Palyginimui: altcoin'ų „pirkti ir laikyti“ per tą patį laiką 1000 → 620 (−9 %/m.), BTC+ETH 1000 → ~800.

## 1. EI3v2_tag_cofi_green (Freqtrade, kripto)
- **Atskiras aprašas su svertu ir metų rezultatais: `EI3v2/README.md`.** Su 2020–21: 1x +81 %/m. (kritimas 17 %), 2x +210 % (49 %), 2,4x riba.
- Failas: `EI3v2_tag_cofi_green.py`. Šaltinis: keithorange/HUGE_FreqTrade_Strategy_Collection.
- Rinka: top 10 altcoin'ų (XRP, BNB, SOL, DOGE, ADA, TRX, LINK, AVAX, LTC, DOT), spot, 5m žvakės.
- Kas tai: perka kritimus (EWO, RSI, MA nuokrypiai) su BTC trendo ir „pump/dump“ filtrais. Išeina trailing stop'u; nuostolingas pozicijas po kurio laiko uždaro „unclog“ taisyklė.

| %/m | Vid. metų % | Iš viso | Max kritimas | Sandorių/m | Laimi % | Vid. sandoris | Profit factor |
|---|---|---|---|---|---|---|---|
| **25,1** | 21,5 | +207 % (1000 → 3067) | 14,9 % | 368 | 93,5 % | 13 val. (mediana 1,2 val.) | 1,9 |

| 2021* | 2022 | 2023 | 2024 | 2025 | 2026* |
|---|---|---|---|---|---|
| +7,3 % | +15,4 % | +27,4 % | +54,5 % | +16,4 % | +8,2 % |

Patikros:
- ✅ `lookahead-analysis`: 0 iš 20 signalų naudoja ateities duomenis.
- ✅ `recursive-analysis`: be ateities duomenų indikatoriuose.
- ⚠️ Su 1m detalumu (tikslesnis trailing stop) 2025 m.: +11,8 % vietoj +15,8 %. Realiai tikėtina **~+18 %/m.**
- ⚠️ Stop-loss −99 % (praktiškai nėra). Didžiausi pavieniai nuostoliai −43 %, −39 %.

## 2. E0V1E_DCA3 (Freqtrade, kripto)
- Failas: `E0V1E_DCA3.py`. Šaltinis: keithorange/HUGE_FreqTrade_Strategy_Collection.
- Rinka: top 10 altcoin'ų, spot, 5m žvakės.
- Kas tai: greitas kritimų pirkimas (scalping) su iki 3 papildomų pirkimų (DCA), jei kaina krenta toliau.

| %/m | Vid. metų % | Iš viso | Max kritimas | Sandorių/m | Laimi % | Vid. sandoris | Profit factor |
|---|---|---|---|---|---|---|---|
| **17,1** | 14,5 | +120 % (1000 → 2202) | 6,5 % | 215 | 86,5 % | 0,9 val. | 2,8 |

| 2021* | 2022 | 2023 | 2024 | 2025 | 2026* |
|---|---|---|---|---|---|
| +7,6 % | +24,1 % | +9,4 % | +30,5 % | +11,4 % | +3,7 % |

Patikros:
- ✅ `lookahead-analysis`: 0 iš 20 signalų naudoja ateities duomenis.
- ⚠️ DCA: blogiausiu atveju į vieną porą sudedama keli kartai daugiau pinigų.

\* 2021 ir 2026 metai daliniai (lapkr.–gruod. ir saus.–lapkr.).

## 3. NASOSv5_mod3 (Freqtrade, kripto) – pridėta 2026-11-11
- Failas: `NASOSv5_mod3.py`. Šaltinis: HUGE_FreqTrade_Strategy_Collection (NASOS šeima, Rallipanos).
- Rinka: top 10 altcoin'ų, spot, 5m žvakės (+1h informacinės). Ant BTC+ETH beveik neprekiauja (8 sandoriai per 5 m.).
- Kas tai: perka kritimus pagal EWO ir nuokrypį nuo MA, išeina pagal MA/ROI; stop-loss −30 %.

| %/m | Vid. metų % | Iš viso | Max kritimas | Sandorių/m | Laimi % | Vid. sandoris | Profit factor |
|---|---|---|---|---|---|---|---|
| **18,3** | 15,4 | +131 % (1000 → 2312) | 3,3 % | 48 | 97,5 % | 36 val. | 6,1 |

| 2021* | 2022 | 2023 | 2024 | 2025 | 2026* |
|---|---|---|---|---|---|
| +6,3 % | +29,4 % | +8,7 % | +16,6 % | +27,3 % | +4,1 % |

Patikros:
- ✅ `lookahead-analysis` (10 altcoin'ų, 2024–2025): 0 iš 20 signalų.
- ✅ `recursive-analysis`: be ateities duomenų (EWO priklauso nuo pradinių žvakių skaičiaus, bet su numatytu startup – stabilus).
- ✅ Nematytas 2018-01 – 2021-11: +89 %/m., kritimas 20,7 %, kasmet pliuse (2018 +14,8 %, 2019 +28 %, 2020 +74 %, 2021 +356 %).
- ⚠️ 1m detalumu netikrinta. Kitas žingsnis – dry-run.

## 4. ckNSJT_morning (Freqtrade, kripto) – pridėta 2026-11-12
- Failas: `ckNSJT_morning.py`. Šaltinis: RoboticAutomations/freqtradestrategies (rinkinys „AIRA – open code v2“, aplankas ichimoku).
- Rinka: top 10 altcoin'ų, spot, 5m žvakės.

| %/m | Iš viso | Max kritimas | Sandorių/m | Laimi % | Vid. sandoris | Profit factor |
|---|---|---|---|---|---|---|
| **21,2** | +161 % (1000 → 2611) | 17,2 % (balanso 37 %) | 256 | 93,4 % | 39 val. | 1,64 |

| 2021* | 2022 | 2023 | 2024 | 2025 | 2026* |
|---|---|---|---|---|---|
| +11,7 % | −14,0 % | +28,7 % | +92,7 % | +20,4 % | −8,9 % |

Patikros:
- ✅ `lookahead-analysis`: 0 iš 20 signalų.
- ✅ Su 0,15 % mokesčiu: +19,0 %/m. (vos krenta).
- ✅ Nematytas 2018–2021: +89,9 %/m., visi metai pliuse (+37, +30, +52, +341 %), kritimas 39 %.
- ⚠️ 2022 ir 2026 minuse, didžioji pelno dalis – 2024. Balanso kritimas iki 37 % – didesnis nei EI3v2.

## Potencialūs, bet rizikingi
| Strategija | Rinka | %/m | Max kritimas | Kodėl ne pagrindiniame sąraše |
|---|---|---|---|---|
| Ichimoku_v37 | BTC+ETH spot, 4h | 15,9 | 16,1 % | 2022–2024 visi metai minuse, laimi 16 % sandorių, ~19 sandorių/m. (tik trendo bangos). Švari; nematytame 2018–21 +89 %/m. |
| Ichimoku_v2 | BTC+ETH spot, 4h | 17,3 | 27 % (balanso 42 %) | 2022 −24 %, ~14 sandorių/m., beveik visas pelnas 2024–25. Švari (lookahead 0/20), 5m detalumas tas pats, nematytame 2018–21 +89 %/m. (2018 −24 %). `Ichimoku_v2.py` |
| Ichimoku_v16 | BTC+ETH spot, 1d | 22,4 | 29 % (balanso 44 %) | tik ~6 sandoriai/m., 2025 +98 % sudaro didžiąją pelno dalį. Švari, 2018–21 +91 %/m., bet 2018 −33 %. `Ichimoku_v16_1d.py` |
| Ichimoku_v5 | alts10 spot, 4h | 17,1 | 20 % (balanso 32 %) | 2022 −16 %, 2025 −14 %, 2024 +110 % (pelnas bangomis), ~97 sandoriai/m. Švari, 5m detalumas tas pats, 2018–21 +105 %/m. (2018 −7,5 %). `Ichimoku_v5.py` |
| Ichimoku_v8 | BTC+ETH spot, 4h | 15,1 | 30 % (balanso 40 %) | 2022 −9 %, 2023 −15 %, 2018 −45 %. Švari, 2018–21 +63 %/m. `Ichimoku_v8.py` |
| VolatilitySystem | BTC+ETH futures, 1h | 69,8 | 53,4 % | 2x svertas, be stop-loss; ant altcoin'ų tik +0,6 %/m.; 2026 m. −0,2 %. Lookahead švari. Failas `VolatilitySystem.py`. |
| EI3v2_tag_cofi_green ant 3x ETF, 1d | 18 sintetinių 3x ETF (TQQQ, UPRO, NUGT, JNUG…) | 13,5 | 14,5 % | Žemiau 14 %; grafikas parinktas iš 4 bandytų. Kasmet teigiama. Žr. `etf3x/README.md`. |

## Atmesti (kad netestuotume iš naujo)
- TheForce (batch50i, 15m): 0,1 % mokesčiu BTC+ETH +89 %/m., alts10 +362 %/m. (išlaiko ir 1m detalumą, lookahead 0/20), bet ~10 tūkst. sandorių/m. po +0,04 %. Su 0,15 % mokesčiu (realus slippage) BTC+ETH −55 %/m., kritimas 99 %. Netinka.
- NowoIchimoku1hV2 (batch50h): 1h testas +35 %/m. (alts10), +32 %/m. (BTC+ETH), švari, išlaikė 2018–21, bet su 5m detalumu tik +6,5 / +10,9 %/m., kritimas 29 / 21 %. Rezultatas buvo išpūstas 1h žvakių.
- NostalgiaForInfinityX8: naudoja ateities duomenis.
- MomentumRegimeBasket (batchM2, 1d): BTC+ETH +17,1 %/m., bet lookahead-analysis rado ateities duomenis (10/10 įėjimų ir 10/10 išėjimų), 2018–21 „+101 %/m.“ – neįmanomai gerai. Atmesta.
- GodStraNew7 (batchM6, 5m): alts10 +16,8 %/m., bet lookahead-analysis 18/20 įėjimų su ateities duomenimis. Atmesta.
- ichiV1: perka Heikin-Ashi kainomis + žiūri į ateitį; ištaisyta versija −58,6 %.
- In & Out TQQQ/TMF: 2021–2026 pralaimi SPY, 2022 m. −55 %.

## Patikra su nematytais 2018–2021 m. (2026-11-10)
Tos pačios taisyklės, mokestis 0,1 %, `freqtrade/results/oos_ei3/`. 2018 m. altcoin'ai krito ~80 %.

| | Monetos | %/m | Max kritimas | 2018 | 2019 | 2020 | 2021* |
|---|---|---|---|---|---|---|---|
| EI3v2_tag_cofi_green | dabartinis top 10 | 134,7 | 16,4 % | +30 % | +30 % | +81 % | +780 % |
| EI3v2_tag_cofi_green | 2018 m. top 9 (be išgyvenusiųjų iškraipymo) | 71,3 | 17,4 % | +46 % | +6 % | +61 % | +220 % |
| E0V1E_DCA3 | dabartinis top 10 | 91,3 | – | +37 % | +22 % | +55 % | +360 % |
| E0V1E_DCA3 | 2018 m. top 9 | 70,0 | 4,9 % | +64 % | +15 % | +54 % | +170 % |

\* 2021 iki lapkričio 8 d. 2018 m. top 9: XRP, LTC, XLM, ADA, TRX, NEO, IOTA, BNB, ETC (EOS duomenų nėra).
Su 1 min. detalumu (2020 m.): EI3v2 +81 % → +61 %, E0V1E_DCA3 +56 % → +46 % (~¼ mažiau).
**Išvada: abu botai išlaikė nematytą laikotarpį ir be išgyvenusiųjų iškraipymo, kiekvienais metais pliuse.**
Realistiškai 2021–26: EI3v2 ~18 %/m., E0V1E_DCA3 ~13 %/m. Kitas žingsnis – dry-run.

## Kitas žingsnis
Dry-run (demo) 1–2 mėn. abiem botams ant tų pačių 10 altcoin'ų. Tik tada maža reali suma.
