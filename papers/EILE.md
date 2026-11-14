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
| 47 | Artumas metų maksimumui kripto skerspjūvyje (George, Hwang metodas) | kripto | ❌ atmesta (2021–26 −48 %/m.; long-short +2 %) → `47_52wh_crypto/REZULTATAI.md` |
| 48 | Crypto Fear & Greed indeksas: kontrarinis ir trendo (FGI > 60) | kripto | ⚠️ kontrarinis ❌; trendas BTC+ETH +24,5 %/m., kritimas 28 %, zona +12…+25 → `48_fear_greed/REZULTATAI.md` |
| 49 | Hash Ribbons (C. Edwards 2019), BTC | kripto | ❌ atmesta (2021–26 +4…+10 %/m., kritimai 48–74 %) → `49_hash_ribbons/REZULTATAI.md` |
| 50 | Connors RSI(2) ant SPY/QQQ/IWM ir 3x ETF | ETF | ❌ atmesta (1x +2…+6 %/m.; 3x ≤ +14 %, 2010–15 +5 %) → `50_connors_etf/REZULTATAI.md` |
| 51 | PlanB Stock-to-Flow ir Bitcoin Rainbow | kripto | ❌ atmesta (S2F modelis žlugo po 2021; Rainbow ≤ +7,5 %/m., kritimas 64–71 %) → `51_s2f_rainbow/REZULTATAI.md` |
| 52 | Atidarymo tarpo prekyba ETF (gap fade / gap and go) | ETF | ❌ atmesta (visi variantai −17…+3 %/m.) → `52_gap_fade/REZULTATAI.md` |
| 53 | MVRV ciklas ir MVRV trendas (Mahmudov, Puell 2018), BTC/ETH | kripto | ❌ atmesta (ciklas 8 sandoriai, nuo 2024 grynieji; trendas ≈ kainos SMA, ETH neveikia) → `53_mvrv/REZULTATAI.md` |
| 54 | Coinbase premija (Coinbase vs Binance kaina), BTC/ETH 1h | kripto | ⚠️ signalas yra (išlieka su 2 h vėlavimu), bet slenksčio smailė, pelnas 2024 m., 2025 −21 % → `54_coinbase_premium/REZULTATAI.md` |
| 55 | Stablecoin emisija (USDT+USDC pasiūla) ir NVT Signal (Woo 2018), BTC/ETH | kripto | ❌ atmesta (emisija – vienas 2022–23 epizodas ≈ SMA filtras, ETH neveikia; NVT −13…+11 %/m.) → `55_stablecoin_nvt/REZULTATAI.md` |
| 56 | Kimchi premija (Upbit vs Binance), BTC/ETH/XRP 1d | kripto | ❌ atmesta (kontrarinis veikė tik 2017–18, trendo ženklas keičiasi, kritimai 50–90 %) → `56_kimchi/REZULTATAI.md` |
| 57 | FED grynasis likvidumas (WALCL − TGA − RRP) → SPY/QQQ/BTC | akcijos, kripto | ❌ atmesta (2023–26 visi variantai gerokai žemiau laikymo) → `57_net_liquidity/REZULTATAI.md` |
| 58 | Taker buy ratio (order imbalance), BTC/ETH ir top 50 skerspjūvis, 1d | kripto | ❌ atmesta (laiko eilutė nestabili, skerspjūvis −41…−1 %/m.) → `58_taker_imbalance/REZULTATAI.md` |
| 59 | IBS atšokimas (Pagonidis 2013), SPY/QQQ/IWM/DIA/EFA/TLT/GLD | ETF | ❌ atmesta (2013–19 gerokai žemiau laikymo; 2020–26 QQQ +27 % tik su MOC vykdymu) → `59_ibs/REZULTATAI.md` |
| 60 | Atvirų pozicijų (OI) signalai: kainos/OI kvadrantai, OI šuolis, skerspjūvis (Bybit) | kripto | ❌ atmesta (nėra pastovaus dėsningumo tarp monetų ir periodų) → `60_open_interest/REZULTATAI.md` |
| 61 | Obligacijų mėnesio pabaigos efektas (TLT/IEF/TMF) | ETF | ⚠️ efektas pastovus 2003–26, bet 1x +4…+6 %/m.; TMF 2010–26 +15…+17 % (2020–26 +8…+11 %), kritimas 28 % → `61_bond_month_end/REZULTATAI.md` |
| 62 | VIX šuolio pirkimas (Connors VIX Stretches, VIX > 30/40, VIX/SMA10) SPY/QQQ | ETF | ❌ atmesta (+1…+15 %/m., nelenkia laikymo; 2008 m. kritimas 41–46 %) → `62_vix_spike/REZULTATAI.md` |
| 63 | Sverto ETF nusidėvėjimo sandoris (short TQQQ+SQQQ ir kt.) | ETF | ❌ atmesta (be skolinimosi +0…+10 %/m., su 3–8 % kaštais ~0 ar minusas) → `63_letf_decay/REZULTATAI.md` |
| 64 | Mėnulio fazių efektas (Dichev, Janes 2003), SPY ir BTC | akcijos, kripto | ❌ atmesta (t = 0,3–1,0; po paskelbimo SPY apsivertė) → `64_lunar/REZULTATAI.md` |
| 65 | Tinklo augimas (aktyvūs adresai; Liu, Tsyvinski 2021), BTC/ETH ir 15 monetų skerspjūvis | kripto | ❌ atmesta (laiko eilutė ≤ SMA; skerspjūvio pranašumas dingsta su 7 d. vėlavimu, tik 2025 m.) → `65_network_growth/REZULTATAI.md` |
| 66 | Aukso/sidabro santykio rotacija; Gundlacho vario/aukso signalas SPY↔TLT | ETF | ❌ atmesta (GSR iki 2020 < GLD; vario/aukso 2021–26 −7…+3 %/m.) → `66_gold_ratios/REZULTATAI.md` |
| 67 | Wikipedia dėmesio signalas (Kristoufek 2013), BTC/ETH | kripto | ❌ atmesta (≈ momentum su filtru, kainos filtrai tokie pat ar geresni) → `67_wiki_attention/REZULTATAI.md` |
| 68 | Bull Market Support Band (20 sav. SMA + 21 sav. EMA), BTC/ETH/alts10 | kripto | ❌ atmesta (BTC 2022–26 +12,7 %, kritimas 45 %; alts +4,9 %; ≈ SMA filtras) → `68_bmsb/REZULTATAI.md` |
| 69 | Fibonacci golden pocket (0,618 atatranka), 12 monetų 4h/1d | kripto | ❌ atmesta (visi variantai minuse, laimi 10–30 %) → `69_fib_golden_pocket/REZULTATAI.md` |
| 70 | Azijos sesijos diapazono pramušimas (00–08 UTC), BTC/ETH/SOL 1h | kripto | ❌ atmesta (2022–26 visi variantai −10…−68 %/m.) → `70_asian_range/REZULTATAI.md` |
| 71 | Opcionų galiojimo savaitės efektas (Stivers, Sun 2013), SPY/QQQ/UPRO/TQQQ | akcijos | ❌ atmesta (veikė tik 2013–19, 2020–26 apsivertė) → `71_opex_week/REZULTATAI.md` |
| 72 | TradingView „Lorentzian Classification“ (kNN, jdehorty), BTC/ETH/SOL/XRP 4h/1d | kripto | ❌ atmesta (2022–26 −74…+10 %/m.) → `72_lorentzian/REZULTATAI.md` |
| 73 | TradingView populiarieji II: Range Filter, HalfTrend, Coral Trend, Pivot Reversal, Donchian Ribbon | kripto | ❌ atmesta (2022–26 visi −24…+11 %/m.) → `73_tv_trend2/REZULTATAI.md` |
| 74 | Kripto mėnesių sezoniškumas („Uptober“, be rugsėjo, IV ketv.), BTC/ETH | kripto | ❌ atmesta (walk-forward 2020–26 BTC +3,5 %/m. prieš laikymo +38,5 %) → `74_crypto_months/REZULTATAI.md` |
| 75 | Jason Kelly 3Sig / 9Sig (ketvirtinis tikslinis perbalansavimas) | ETF | ❌ atmesta (3Sig < laikymas; 9Sig 2000–09 −100 %) → `75_3sig/REZULTATAI.md` |
| 76 | Šalių ETF momentum / žemas volatilumas / reversalas (20 iShares) | ETF | ❌ atmesta (2013–19 −1…+2 %/m., ≈ lygūs svoriai) → `76_country_momentum/REZULTATAI.md` |
| 77 | YouTube klasika: MACD+200EMA (1,5R), Stoch RSI trendas, Williams Alligator, Heikin Ashi+EMA50, EMA 9/21 | kripto | ❌ atmesta (2022–26 visi −50…+11 %/m.) → `77_youtube_classics/REZULTATAI.md` |
| 78 | Funding skirtumo arbitražas Binance ↔ Bybit (12 monetų) | kripto | ❌ atmesta (skirtumas 0,5–1 bp/8 h < kaštai; geriausia +0,6 %/m.) → `78_funding_xex/REZULTATAI.md` |
| 79 | „BTC seka M2 su 10 sav. vėlavimu“ (JAV ir JAV+EZ+JP M2) | kripto | ❌ atmesta (vėlavimas blogina; 2024–26 nelenkia SMA200) → `79_m2_btc/REZULTATAI.md` |
| 80 | Naujų Binance listingų nuosmukis (short naujų monetų) | kripto | ❌ atmesta kaip strategija (short tik 2024–26, anksčiau −46…−80 %/m.); ⚠️ filtras: vengti monetų < 90–180 d. → `80_new_listings/REZULTATAI.md` |
| 81 | BTC halvingo ciklas (500 d. prieš – 550 d. po halvingo) | kripto | ⚠️ rizikingų sąraše: 2021–26 +54 %/m. (kritimas 53 %), zona +70…+112 %, bet tik 4 ciklai → `81_halving_cycle/REZULTATAI.md` |
| 82 | Prezidento rinkimų ciklas (S&P 500 1929–2026) | akcijos | ❌ atmesta (priešrinkiminiai metai stiprūs, bet kaip strategija < laikymas) → `82_election_cycle/REZULTATAI.md` |
| 83 | Aukso rudens efektas (Baur 2013), GLD | ETF | ❌ atmesta (po paskelbimo rugsėjis −1,8 %, lapkritis −1,2 % – apsivertė) → `83_gold_autumn/REZULTATAI.md` |
| 84 | Pajamingumo kreivės inversija (T10Y2Y/T10Y3M) → S&P 500 | akcijos | ❌ atmesta (1977–99 ir 2013–26 < laikymas; padeda tik 2000–12) → `84_yield_curve/REZULTATAI.md` |
| 85 | Dolerio indekso (DXY) trendas → BTC/ETH/QQQ | kripto, akcijos | ❌ atmesta (nelenkia laikymo ir SMA200; QQQ tik 2020–26) → `85_dxy_btc/REZULTATAI.md` |
