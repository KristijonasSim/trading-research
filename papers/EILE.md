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
