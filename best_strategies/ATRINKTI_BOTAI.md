# Atrinkti botai

Čia dedame tik tas strategijas, kurios praėjo visus testus. Kriterijus: **≥ 14 %/m.** per paskutinius 5 metus ir švari patikra (nežiūri į ateitį).

Testavimo sąlygos visiems: 2021-11-08 – 2026-11-08, Binance, 0,1 % mokestis, pradžia 1000 USDT.
Palyginimui: altcoin'ų „pirkti ir laikyti“ per tą patį laiką 1000 → 620 (−9 %/m.), BTC+ETH 1000 → ~800.

## 1. EI3v2_tag_cofi_green (Freqtrade, kripto)
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

## Potencialūs, bet rizikingi
| Strategija | Rinka | %/m | Max kritimas | Kodėl ne pagrindiniame sąraše |
|---|---|---|---|---|
| Ichimoku_v37 | BTC+ETH spot, 4h | 15,9 | 16,1 % | 2022–2024 visi metai minuse, laimi 16 % sandorių, ~19 sandorių/m. (tik trendo bangos). Švari; nematytame 2018–21 +89 %/m. |
| VolatilitySystem | BTC+ETH futures, 1h | 69,8 | 53,4 % | 2x svertas, be stop-loss; ant altcoin'ų tik +0,6 %/m.; 2026 m. −0,2 %. Lookahead švari. Failas `VolatilitySystem.py`. |
| EI3v2_tag_cofi_green ant 3x ETF, 1d | 18 sintetinių 3x ETF (TQQQ, UPRO, NUGT, JNUG…) | 13,5 | 14,5 % | Žemiau 14 %; grafikas parinktas iš 4 bandytų. Kasmet teigiama. Žr. `etf3x/README.md`. |

## Atmesti (kad netestuotume iš naujo)
- NowoIchimoku1hV2 (batch50h): 1h testas +35 %/m. (alts10), +32 %/m. (BTC+ETH), švari, išlaikė 2018–21, bet su 5m detalumu tik +6,5 / +10,9 %/m., kritimas 29 / 21 %. Rezultatas buvo išpūstas 1h žvakių.
- NostalgiaForInfinityX8: naudoja ateities duomenis.
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
