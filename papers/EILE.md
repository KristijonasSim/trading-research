# Mokslinių straipsnių strategijos: savaitgalio eilė (2026-11-14–16)

Taisyklės kaip visur: tie patys mokesčiai, lyginti su „pirkti ir laikyti“, kūrimo ir nematytas laikotarpis atskirai.
Kripto duomenys: Binance (spot/futures, 1h/1d, visos USDT poros su istorija). Akcijos/ETF: Yahoo dienos kainos.

| # | Strategija (šaltinis) | Rinka | Būsena |
|---|---|---|---|
| 1 | Kriptovaliutų skerspjūvio momentum, top 50 monetų, savaitinis perbalansavimas (Liu, Tsyvinski, Wu 2022, J. Finance) | kripto | ❌ atmesta (po 2022 visi minuse) → `01_kripto_momentum/REZULTATAI.md` |
| 2 | Trumpalaikis atšokimas (short-term reversal) top 50 monetų, dieninis (Dobrynskaya 2023) | kripto | ❌ atmesta (po 2022 visi minuse) → `01_kripto_momentum/REZULTATAI.md` |
| 3 | Funding rate carry: long mažiausio, short didžiausio funding (Schmeling, Schrimpf, Todorov 2023, BIS) | kripto futures | ❌ atmesta → `03_funding_carry/REZULTATAI.md` |
| 4 | Spot–futures bazės prekyba (cash-and-carry, delta neutrali) | kripto | ❌ atmesta → `03_funding_carry/REZULTATAI.md` |
| 5 | Kripto mažos kapitalizacijos / nelikvidumo premija (Liu, Tsyvinski, Wu 2022) | kripto | ❌ atmesta (po 2022 visi minuse) → `01_kripto_momentum/REZULTATAI.md` |
| 6 | Laiko eilučių momentum su volatilumo taikymu, 20+ futures/ETF (Moskowitz, Ooi, Pedersen 2012) | ETF | ❌ atmesta (2016–26 long-short −1 %/m., long-only +3,6 %/m.) → `06_tsmom/REZULTATAI.md` |
| 7 | Žemo volatilumo / betting-against-beta S&P 500 akcijose (Frazzini, Pedersen 2014) | akcijos | ❌ atmesta (2014–26 +10,8 %/m. vs SPY +13,5 %, kritimas toks pat) → `07_lowvol/REZULTATAI.md` |
| 8 | Pelno anonsų dreifas (PEAD) – reikia nemokamų duomenų, tikrinti ar įmanoma | akcijos | ❌ atmesta (long top 20 % = lygiavertis krepšelis, long-short +1,7 %/m.) → `08_pead/REZULTATAI.md` |
| 9 | Porų prekyba (kointegracija) kripto, 5m–1h (Fil, Kristoufek 2020) | kripto | ❌ atmesta (minusas net be mokesčių) → `09_poros/REZULTATAI.md` |
| 10 | Kripto savaitės dienų ir valandų sezoniškumas, walk-forward (ne visos istorijos) | kripto | ❌ atmesta (efektas 1–2 bp/val., mokestis 20 bp) → `10_sezoniskumas/REZULTATAI.md` |
| 11 | Pre-FOMC dreifas S&P 500 (Lucca, Moench 2015) | akcijos | ❌ atmesta (2012–26 +0,02 % per įvykį, iki 2011 +0,24 %) → `11_fomc/REZULTATAI.md` |
| 12 | 52 savaičių maksimumo momentum S&P 500 (George, Hwang 2004) | akcijos | ❌ atmesta (long +10,5 %/m. < lygiavertis 12,4 %, long-short minuse) → `12_52wh/REZULTATAI.md` |
| 13 | Volatilumu valdomas portfelis SPY/QQQ (Moreira, Muir 2017) | ETF | ⚠️ rizikos mažinimas: QQQ 2016–26 +17,7 %/m., kritimas 21 % (laikymas +19,1 %, 35 %) → `13_volmanaged/REZULTATAI.md` |
| 14 | Akcijų kalendorinio mėnesio sezoniškumas S&P 500 (Heston, Sadka 2008) | akcijos | ❌ atmesta (2014–26 long +10,3 %/m., long-short −3,3 %) → `14_seasonality/REZULTATAI.md` |
| 15 | Kripto žemo volatilumo anomalija (Burggraf, Rudolf 2021) | kripto | ❌ atmesta (spot teoriškai +85 %/m., su perp ir funding −8,5 %/m.) → `15_kripto_lowvol/REZULTATAI.md` |
| 16 | Kripto MAX / loterijos efektas (Li ir kt. 2021) | kripto | ❌ atmesta kartu su 15 (2018–21 −13 %/m., short neįgyvendinamas) |
| 17 | Liekamasis momentum S&P 500 (Blitz, Huij, Martens 2011) | akcijos | ❌ atmesta (2014–26 +13,8 %/m. = SPY, kritimas 39 %) → `17_resmom/REZULTATAI.md` |
| 18 | Jesse klasika: Turtle, Dual Thrust (kripto, 1d) | kripto | ⚠️ Dual Thrust BTC+ETH +11,9 %/m., kritimas 11 %, kasmet pliuse; Turtle +14 %/m., kritimas 30 % → `18_turtle/REZULTATAI.md` |
| 19 | Larry Williams volatilumo pramušimas (kripto, 1d) | kripto | ❌ atmesta (2021–26 BTC+ETH −9…+5 %/m.) → `19_larry_vb/REZULTATAI.md` |
| 20 | R-Breaker (BTC/ETH, 1h) | kripto | ⚠️ tik trendas long +15,2 %/m. (0,05 %), kritimas 13 %; koreliacija su Dual Thrust 0,76 → `20_rbreaker/REZULTATAI.md` |
| 21 | Pruitt/Hill klasika: Aberration, King Keltner, Bollinger Bandit, DBO II, Thermostat (kripto 1d) | kripto | ⚠️ Aberration BTC+ETH +17,8 %/m., kritimas 27 %; kitos +7…17 %, kritimai 34–42 % → `21_pruitt/REZULTATAI.md` |
| 22 | Paprasti trendo filtrai (Faber 10 mėn., 50/200, SMA200) kripto | kripto | ❌ atmesta (2021–26 −4…+13 %/m., kritimai 36–65 %) → `22_trend_filters/REZULTATAI.md` |
| 23 | Klasika II: Darvas, Raschke Holy Grail / Turtle Soup, Parabolic SAR, Alligator, Seykota (kripto 1d) | kripto | ❌ atmesta (2021–26 −19…+7 %/m.) → `23_classics2/REZULTATAI.md` |
| 24 | BTC ciklo indikatoriai: Mayer daugiklis, Pi Cycle Top, 200 sav. vidurkis | kripto | ❌ atmesta (per mažai signalų, kritimai 53–83 %) → `24_btc_cycle/REZULTATAI.md` |
| 25 | Larry Connors: RSI(2), kaupiamasis RSI, ConnorsRSI, dvigubas 7 d. (kripto 1d) | kripto | ❌ atmesta (BTC+ETH 2021–26 ≤ +11,7 %/m., bet 2018–21 ~0; alts10 po 2021 ~0) → `25_connors/REZULTATAI.md` |
| 26 | Dienos vidaus momentum: paskutinė valanda pagal dieną (Gao ir kt. 2018; Wen ir kt. 2022), kripto 1h | kripto | ❌ atmesta (efektas yra, bet su 0,05 % mokesčiu −14…−30 %/m.) → `26_intraday_mom/REZULTATAI.md` |
| 27 | Trendo klasika III: KAMA (Kaufman), Supertrend, Hull MA, Chandelier exit (kripto 1d) | kripto | ❌ atmesta (2021–26 dauguma −9…+7 %/m., kritimai 31–68 %; HMA(100) +21 % – pavienė) → `27_trend3/REZULTATAI.md` |
| 28 | Mėnesio sandūros efektas (Lakonishok, Smidt 1988; McConnell, Xu 2008), ETF ir kripto | ETF / kripto | ❌ atmesta (SPY +7,3 %/m. prieš 14,6; kripto po 2021 minuse) → `28_tom/REZULTATAI.md` |
| 29 | Toby Crabel NR4/NR7/inside day pramušimas (kripto 1d) | kripto | ❌ atmesta (long ≤ +9 %/m.; long-short NR4 +17,9 % tik su 0,05 %, metai −5…+57, NR7 +5,8) → `29_crabel/REZULTATAI.md` |
| 30 | Nakties grąžos premija: laikyti tik nakčiai (Cooper, Cliff, Gulen 2008), ETF | ETF | ❌ atmesta (efektas yra, bet su 0,01 % kaštais nelenkia laikymo) → `30_overnight/REZULTATAI.md` |
| 31 | BTC CME gap'o užpildymas (populiarus teiginys) | kripto | ❌ atmesta (užsipildo 50–70 % per 5 d., bet BTC visi variantai minuse) → `31_cme_gap/REZULTATAI.md` |
| 32 | Funding rate kontrarinis signalas: long perp kai funding žemiau neutralaus (BTC/ETH) | kripto futures | ⚠️ BTC+ETH 2021–26 +26 %/m., kritimas 30 %, zona +13…+26; alts10 neveikia → `32_funding_timing/REZULTATAI.md` |
| 33 | BTC ↔ altcoin'ų rotacija (Altcoin Season Index, dvigubas momentum) | kripto | ❌ atmesta (2021–26 visi −6…−24 %/m.) → `33_altseason/REZULTATAI.md` |
| 34 | Volatilumu valdomas kripto laikymas (Moreira, Muir metodas), BTC/ETH | kripto | ❌ atmesta (su trendo filtru ≤ +13 %/m., kritimas 36 %) → `34_crypto_volmanaged/REZULTATAI.md` |
| 35 | Noise Breakout (Zarattini ir kt. 2024) ant BTC/ETH 1h | kripto | ❌ atmesta (visi variantai minuse) → `35_noise_crypto/REZULTATAI.md` |
| 36 | Kripto laiko eilučių momentum 1–4 sav. (Liu, Tsyvinski 2021 RFS) | kripto | ❌ atmesta (1 sav. 2021–26 −7…−21 %/m.; 8 sav. +15 % su 53 % kritimu) → `36_tsmom_crypto/REZULTATAI.md` |
| 37 | TTM Squeeze (Carter) ir Bollinger Squeeze, kripto 1d | kripto | ❌ atmesta (originalas +3 %/m.; geriausias parametras +14,6 %, tipiškai ~9 %) → `37_squeeze/REZULTATAI.md` |
| 38 | TradingView populiarieji: UT Bot, WaveTrend, SSL Channel, QQE (kripto 1d) | kripto | ❌ atmesta (2021–26 −5…+8 %/m., kritimai 37–67 %) → `38_tv_popular/REZULTATAI.md` |
| 39 | Savaitinis trumpalaikis atšokimas S&P 500 (Lehmann 1990, Jegadeesh 1990) | akcijos | ❌ atmesta (2014–26 ≤ +10,5 %/m. < SPY 13,5 %) → `39_st_reversal/REZULTATAI.md` |
| 40 | BTC → altcoin'ų vėlavimas (lead-lag), 1h | kripto | ❌ atmesta (koreliacija −0,03; su mokesčiais minusas) → `40_leadlag/REZULTATAI.md` |
| 41 | Spot grid botas (Binance/Pionex Spot Grid), BTC/ETH 5m | kripto | ❌ atmesta (0,1 %: −18…+9 %/m., kritimai 54–93 %) → `41_grid/REZULTATAI.md` |
| 42 | BTC/ETH mėnesinio opcionų galiojimo efektas (Deribit) | kripto | ❌ atmesta (2019–22 veikė, 2023–26 BTC +4 %/m., ETH −2 %) → `42_expiry/REZULTATAI.md` |
| 43 | Halloween / Sell in May (Bouman, Jacobsen 2002), ETF ir BTC | ETF / kripto | ❌ atmesta (2016–26 perpus mažiau už laikymą, kritimai tie patys) → `43_halloween/REZULTATAI.md` |
| 44 | Apyvartos šuolio premija kripto (Gervais ir kt. 2001; Liu ir kt. 2022) | kripto | ❌ atmesta (blogiau už krepšelį abiem laikotarpiais) → `44_volume_shock/REZULTATAI.md` |
| 45 | Paired Switching SPY/TLT, QQQ/IEF, SPY/GLD (Maewal 2017) | ETF | ❌ atmesta (2016–26 nelenkia laikymo) → `45_paired_switch/REZULTATAI.md` |
| 46 | 3Commas stiliaus DCA botas (TP + apsauginiai orderiai), 12 monetų 5m | kripto | ❌ atmesta (geriausias +11 %/m., kritimas 43 %; 2022 −36…−65 %) → `46_dca_bot/REZULTATAI.md` |
