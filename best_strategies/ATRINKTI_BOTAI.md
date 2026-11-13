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
- ⚠️ Su 1m detalumu (tikslesnis trailing stop, 2026-11-13 visi metai): 2022 +5,5 % (vietoj +15,4), 2023 +25,9 (+27,4), 2024 +43,9 (+54,1), 2025 +11,8 (+15,8). Vidurkis ~21 %/m. vietoj ~28 %, visi metai pliuse. Realiai tikėtina **~+18 %/m.**
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
- ⚠️ Su 1m detalumu (2026-11-13, metai atskirai, `config_spot_market.json`): 2022 +12,2 % (vietoj +24,1), 2023 +11,7 (+9,4), 2024 +22,9 (+30,4), 2025 +2,1 (+11,5). Vidurkis ~12 %/m. vietoj ~19 % – 5m testas išpučia ~⅓ (greiti sandoriai, 0,9 val.). Realiai tikėtina **~+11…13 %/m.**, žemiau 14 % ribos.

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
- ✅ Su 1m detalumu (2026-11-13, metai atskirai): 2022 +26,4 % (vietoj +27,9), 2023 +8,5 (+8,7), 2024 +15,6 (+16,5), 2025 +56,9 (+27,3). Rezultatas nepablogėja, `freqtrade/results/validate50/detail_q.log`. Kitas žingsnis – dry-run.

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
- ✅ Su 1m detalumu (2026-11-13, `config_spot_market.json`): 2022 −0,3 % (vietoj −9,5), 2023 +31,2 (+29,2), 2024 +85,3 (+88,8), 2025 +31,1 (+20,4). Nepablogėja.
- ⚠️ 2022 ir 2026 minuse, didžioji pelno dalis – 2024. Balanso kritimas iki 37 % – didesnis nei EI3v2.

## 5. MACDVStrategy (Freqtrade, BTC+ETH, 1d) – pridėta 2026-11-13
- Failas: `MACDVStrategy.py`. Šaltinis: github.com/thino-dev/Freqtrade_Strategies.
- Taisyklė: perka, kai kaina virš 200 d. vidurkio ir MACD-V (MACD padalintas iš ATR) > 70; parduoda po +2,85 % dienos žvakės, MACD kirtimo žemyn arba po 15/77 d.
- 2021-11 – 2026-11, BTC+ETH: **+16,0 %/m., kritimas 14,7 %**, 59 sandoriai (rinka per tą laiką −22,5 %). Metai: 2021 −7 %, 2022 −8 %, 2023 +47 %, 2024 +25 %, 2025 +36 %, 2026 −2 %.
- Nematytas 2018–2021: **+72,6 %/m., kritimas 12 %** (2019 +44 %, 2020 +109 %, 2021 +172 %). Altcoin'ai: +48 %/m., kritimas 7 %.
- Lookahead-analysis: 0/20 šališkų signalų (`results/validation/MACDVStrategy_batchM22.log`).
- ✅ Su 5m detalumu (2026-11-13): +15,7 %/m. (be detalumo +16,0 %), balanso kritimas 21 %. `freqtrade/results/validate50/detail_MACDVStrategy_btc_eth_*_full`
- ⚠️ Kylančioje rinkoje atsilieka nuo „pirkti ir laikyti“ (2018–21 BTC+ETH laikymas +823 %); vertė – maži kritimai. Ant altcoin'ų 2021–26 tik +10,5 %/m.

## 6. Aberration (Keith Fitschen 1993; BTC+ETH, 1d) – pridėta 2026-11-13
- Failas: `freqtrade/user_data/strategies/papers/Aberration.py`. Šaltinis: K. Fitschen, „Aberration“ (komercinė sistema nuo 1993, aprašyta „Building Winning Algorithmic Trading Systems“).
- Taisyklė: perka, kai uždarymas > SMA35 + 2σ; parduoda, kai uždarymas < SMA35. Tik long, be stop-loss.
- 2021-11 – 2026-11, BTC+ETH (freqtrade): **+18,4 %/m., balanso kritimas 28 %**, 40 sandorių. Metai: 2022 −15 %, 2023 +63 %, 2024 +49 %, 2025 +23 %, 2026 −5 %.
- Nematytas 2018–2021 (pandas, `papers/21_pruitt/`): +88 %/m., kritimas 34 %. Altcoin'ai 2021–26 tik +11,6 %/m. (kritimas 42 %).
- Lookahead-analysis: 0/20 (`results/validation/Aberration_lookahead.log`). Signalai dienos uždarymu, be stop'ų, todėl detalumas įtakos neturi.
- ⚠️ Tik ~8 sandoriai per metus, pelnas bangomis (kaip Ichimoku), kritimas didesnis nei MACDVStrategy. Koreliuoja su MACDV (abi BTC+ETH trendo).
- ⚠️ Parametrų jautrumas (SMA 20–60, σ 1,5–2,5): 2021–26 nuo +1,6 iki +24,7 %/m., mediana ~12 %. Originalūs 35/2 – virš vidurkio, realistiškai tikėtina ~12 %/m. (`papers/21_pruitt/REZULTATAI_aberration_jautrumas.txt`). 2018–21 visos kombinacijos +44…+114 %/m.

## 7. EMAPriceCrossoverWithTreshold (Freqtrade, BTC+ETH, 1h) – pridėta 2026-11-13
- Labai paprasta: perka, kai kaina kerta 800 val. EMA iš apačios; parduoda, kai nukrenta 1 % po ja; stop-loss −15 %.
- 2022–26: **+21,4 %/m.**, kritimas 23,9 %, 241 sandoris (2022 −14 %, 2023 +23 %, 2024 +109 %, 2025 +11 %, 2026 +7 %).
- Nematytas 2018–21: **+89,8 %/m.**, kritimas 13,2 % (2018 −22 %, 2019 +114 %, 2020 +146 %, 2021 +186 %). Altcoin'ams +42 %/m., kritimas 23,5 %.
- Ateities duomenų nenaudoja (lookahead 0/20, `results/validation/EMAPriceCrossoverWithTreshold_batchM24.log`).
- Minusas: krentančiais metais (2018, 2022) praranda 14–22 %, laimi tik ~20 % sandorių.
- ✅ Su 5m detalumu (2026-11-14): +21,4 %/m. – tas pats. Dry-run nuo 2026-11-14 (`freqtrade/dryrun/`).
- Šaltinis: erdincyasar/freqtrade_kanaxe. Failas `best_strategies/EMAPriceCrossoverWithThreshold.py`.

## 8. abbas (Freqtrade, altcoin'ai, 5m) – pridėta 2026-11-14
- 2021–26 (alts10): **+14,2 %/m., kritimas 8,7 %**, 1857 sandoriai; kasmet pliuse, išskyrus 2026 (−0,5 %).
- Nematytas 2018–21: dabartinis top 10 +63 %/m. (kritimas 12 %), **2018 m. top 9 +51 %/m. (kritimas 18 %)**.
- Su 1 min. detalumu (2020): +49 % → +39 %. Lookahead 0/20.
- Šaltinis: thinkong/freqtradestrategies. Failas `best_strategies/abbas.py`.

## 9. NASMAO (Freqtrade, altcoin'ai, 5m) – pridėta 2026-11-14
- 2021–26 (alts10): **+18,2 %/m., kritimas 16,2 %**, 839 sandoriai (2022 −1,9 %, 2026 −0,2 %).
- Nematytas 2018–21: top 10 +41 %/m. (kritimas 15 %), 2018 m. top 9 +28,5 %/m. (kritimas 19 %).
- Su 1 min. detalumu (2020): +34 % → +28 %. Lookahead 0/20.
- ⚠️ Giminingas NASOSv5_mod3 (nr. 3), signalai gali sutapti.
- Šaltinis: flessner/freqtrade-stuff. Failas `best_strategies/NASMAO.py`.

## 10. SMAO (Freqtrade, altcoin'ai, 5m) – pridėta 2026-11-14
- 2021–26 (alts10): +15,1 %/m., **kritimas 31,4 %** (2025 −8,5 %).
- Nematytas 2018–21: top 10 +100 %/m. (kritimas 36 %), 2018 m. top 9 +65 %/m. (kritimas 32 %).
- Su 1 min. detalumu (2020): nepakito (+70 %). Lookahead 0/20.
- ⚠️ Didžiausi kritimai iš šių trijų.
- Šaltinis: flessner/freqtrade-stuff. Failas `best_strategies/SMAO.py`.

## 11. Passivbot trailing martingale (TWEL 0,75; BTC, ETH + alts10, futures) – pridėta 2026-11-14
- Autoriaus konfigas `configs/examples/default_trailing_martingale_long.json` (enarjord/passivbot), tik ekspozicija sumažinta iki 0,75 ir monetos – mūsų standartinės 12.
- 2021–26: **+21,1 %/m., kritimas 25 %**, kasmet pliuse (2022 +21 %, 2026 +9 %). Su 0,1 % mokesčiu +17,8 %/m.
- Nematytas 2019-12 – 2021-04 (autorius optimizavo nuo 2021-04): **+69,8 %/m., kritimas 37 %**.
- Su 2021-11 top 20 monetų (įskaitant žlugusį FTT, be LUNA – nėra duomenų): +26,3 %/m., kritimas 24 %.
- Funding neįskaičiuotas, įvertis ±1–2 %/m. ⚠️ Martingale: kritimuose didina poziciją; 1,5 ekspozicija duoda +49 %/m., bet kritimas 51–73 %.
- Aprašas ir skriptai `passivbot/REZULTATAI.md`; paleidimas – Docker `passivbot:stamped`.

## Potencialūs, bet rizikingi
| Strategija | Rinka | %/m | Max kritimas | Kodėl ne pagrindiniame sąraše |
|---|---|---|---|---|
| Ichimoku_v37 | BTC+ETH spot, 4h | 15,9 | 16,1 % | 2022–2024 visi metai minuse, laimi 16 % sandorių, ~19 sandorių/m. (tik trendo bangos). Švari; nematytame 2018–21 +89 %/m. |
| Ichimoku_v2 | BTC+ETH spot, 4h | 17,3 | 27 % (balanso 42 %) | 2022 −24 %, ~14 sandorių/m., beveik visas pelnas 2024–25. Švari (lookahead 0/20), 5m detalumas tas pats, nematytame 2018–21 +89 %/m. (2018 −24 %). `Ichimoku_v2.py` |
| Ichimoku_v16 | BTC+ETH spot, 1d | 22,4 | 29 % (balanso 44 %) | tik ~6 sandoriai/m., 2025 +98 % sudaro didžiąją pelno dalį. Švari, 2018–21 +91 %/m., bet 2018 −33 %. `Ichimoku_v16_1d.py` |
| Ichimoku_v5 | alts10 spot, 4h | 17,1 | 20 % (balanso 32 %) | 2022 −16 %, 2025 −14 %, 2024 +110 % (pelnas bangomis), ~97 sandoriai/m. Švari, 5m detalumas tas pats, 2018–21 +105 %/m. (2018 −7,5 %). `Ichimoku_v5.py` |
| Ichimoku_v8 | BTC+ETH spot, 4h | 15,1 | 30 % (balanso 40 %) | 2022 −9 %, 2023 −15 %, 2018 −45 %. Švari, 2018–21 +63 %/m. `Ichimoku_v8.py` |
| Dual Thrust (n=4, k=0,7) | BTC+ETH spot, 1d (įėjimas dienos viduje) | 11,9 (perp 0,05 %: 13,8) | 11 % | Žemiau 14 %; bet kasmet pliuse 2018–2026 (perp 2020–26 taip pat). Freqtrade versija `freqtrade/user_data/strategies/papers/DualThrust.py`: +11,7 %/m., kritimas 11,5 %, lookahead 0/20, 2018–21 +30 %/m., 5m vykdymas patvirtina. Jautrus mokesčiui (0,15 % → 7,5 %/m.). `papers/18_turtle/` |
| R-Breaker (tik trendas, long) | BTC+ETH perp, 1h | 15,2 (0,05 %) / 10,5 (0,1 %) | 13 % | Ta pati idėja kaip Dual Thrust (koreliacija 0,76), 2018–21 +38,5 %/m. (kritimas 9 %). Funding neįskaičiuotas. `papers/20_rbreaker/` |
| Funding kontrarinis (long kai 3 d. funding < 0,01 %/d.) | BTC+ETH perp, 1d | 26 (0,05 %) / 22 (0,1 %) | 30 % | 2020–21 +31 %/m.; parametrų zona +13…+26 %/m.; ant alts10 neveikia, ETH 2020–21 tik +3,6 % – viską neša BTC. Rinkoje ~30 % laiko. Freqtrade: +26,5 %/m., kritimas 22 %, lookahead signalai 0/20, bet 2025–26 PF tik 1,2/1,05; su 1 d. vėlavimu +15,6 %. `FundingContrarian.py`, `papers/32_funding_timing/` |
| Turtle S2 (55/20) | BTC+ETH spot, 1d | 14,5 | 30 % | 2022 −18 %, 2018–21 +74 %/m. (kritimas 49 %). `papers/18_turtle/` |
| VolatilitySystem | BTC+ETH futures, 1h | 69,8 | 53,4 % | 2x svertas, be stop-loss; ant altcoin'ų tik +0,6 %/m.; 2026 m. −0,2 %. Lookahead švari. Failas `VolatilitySystem.py`. |
| EI3v2_tag_cofi_green ant 3x ETF, 1d | 18 sintetinių 3x ETF (TQQQ, UPRO, NUGT, JNUG…) | 13,5 | 14,5 % | Žemiau 14 %; grafikas parinktas iš 4 bandytų. Kasmet teigiama. Žr. `etf3x/README.md`. |

## Atmesti (kad netestuotume iš naujo)
- ERMD_Strategy_risk (1d): 2023–24 +222 % virsta +8,6 % su 5 min. detalumu – rezultatas tik iš dienos žvakės iliuzijos.
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
