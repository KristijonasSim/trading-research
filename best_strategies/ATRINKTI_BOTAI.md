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

## Potencialūs, bet rizikingi
| Strategija | Rinka | %/m | Max kritimas | Kodėl ne pagrindiniame sąraše |
|---|---|---|---|---|
| VolatilitySystem | BTC+ETH futures, 1h | 69,8 | 53,4 % | 2x svertas, be stop-loss; ant altcoin'ų tik +0,6 %/m.; 2026 m. −0,2 %. Lookahead švari. Failas `VolatilitySystem.py`. |
| EI3v2_tag_cofi_green ant 3x ETF, 1d | 18 sintetinių 3x ETF (TQQQ, UPRO, NUGT, JNUG…) | 13,5 | 14,5 % | Žemiau 14 %; grafikas parinktas iš 4 bandytų. Kasmet teigiama. Žr. `etf3x/README.md`. |

## Atmesti (kad netestuotume iš naujo)
- NostalgiaForInfinityX8: naudoja ateities duomenis.
- ichiV1: perka Heikin-Ashi kainomis + žiūri į ateitį; ištaisyta versija −58,6 %.
- In & Out TQQQ/TMF: 2021–2026 pralaimi SPY, 2022 m. −55 %.

## Kitas žingsnis
Dry-run (demo) 1–2 mėn. abiem botams ant tų pačių 10 altcoin'ų. Tik tada maža reali suma.
