# Rytinė ataskaita 2026-11-14 (antras kompiuteris)

## Naktį patikrinta (straipsniai ir teiginiai 34–82)
Dauguma atmesti. Išgyveno tik kaip „rizikingi“:

| # | Kas | Rezultatas |
|---|---|---|
| 48 | Fear & Greed trendas (BTC+ETH, FGI > 60) | +23 %/m., kritimas 14 % (freqtrade), **dry-run** |
| 54 | Coinbase premija (Coinbase vs Binance kaina, 1h) | BTC/ETH +19 %/m. 2022–26, kritimas 31–37 %; signalas išlieka su 2 h vėlavimu, bet slenksčio smailė, pelnas 2024 m., 2025 −21 % |
| 61 | Obligacijų mėnesio pabaiga (TMF paskutines 5–7 d.) | 2010–26 +15…+17 %/m., kritimas 28 %; 2020–26 tik +8…+11 %; nekoreliuoja su kripto |
| 81 | **BTC halvingo ciklas** (laikyti 500 d. prieš – 550 d. po halvingo) | 2021–26 +54 %/m. (laikymas +14 %), kritimas 53 %; išėjo 2021-11-12 ir 2025-10-22 prie viršūnių; zona +70…+112 %/m.; ETH/alts taip pat. Bet tik 4 ciklai. Kitas įėjimas ~2026-12-02 |

Atmesta (be pranašumo arba neveikia po paskelbimo): MVRV, stablecoin emisija, NVT, Kimchi premija, FED likvidumas, taker buy ratio, IBS, OI signalai, VIX šuolis, sverto ETF nusidėvėjimas, Mėnulio fazės, tinklo augimas (adresai), aukso/sidabro ir vario/aukso santykiai, Wikipedia dėmesys, Bull Market Support Band, Fibonacci 0,618, Azijos diapazonas, Lorentzian Classification (TradingView kNN), 5 TradingView trendo indikatoriai, kripto mėnesių sezoniškumas, OpEx savaitė, 3Sig/9Sig, šalių ETF momentum, YouTube klasika (MACD+200EMA, Stoch RSI, Alligator, Heikin Ashi, EMA 9/21), funding arbitražas tarp biržų, M2 su vėlavimu, naujų listingų short (bet filtras: vengti monetų < 90–180 d.), rinkimų ciklas, gap prekyba, S2F/Rainbow ir kt. Visi aprašai `papers/EILE.md`.

## Passivbot martingale (nr. 11) – svarbi pataisa
- Binance duomenimis 2021–26: +21,1 %/m., kritimas 25 %.
- **Bybit duomenimis ta pati konfigūracija: +11,3 %/m., kritimas 31 %, 2022 −21 %.** Skirtumas – LTC ir LINK (kitokie dagčiai). Martingale rezultatas jautrus konkrečiam kainų keliui; kadangi demo būtų Bybit, realistiškas lūkestis ~10–20 %/m.

## Dry-run (šis kompiuteris, 7 botai, `freqtrade/dryrun/`)
Visi veikia. Per pirmas ~6 val. – 1 sandoris (FundingContrarian −0,89 USDT); rinka krenta (FGI ~20), todėl trendo botai laukia.

## Laukia sprendimo
1. Passivbot martingale į Bybit demo (raktai kitame kompiuteryje).
2. Ar Coinbase premiją ir TMF mėnesio pabaigą verta perkelti į dry-run (abi rizikingos).
