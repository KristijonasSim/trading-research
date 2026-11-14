# Trading research — suvestinė (2026-11-09)

## Kas padaryta
1. **65 strategijų backtestai** su Freqtrade: oficialus `freqtrade-strategies` repo ir NostalgiaForInfinityX8.
   - Laikotarpis 2021-11-08 – 2026-11-08, Binance.
   - Dvi grupės: BTC+ETH ir top 10 altcoin'ų.
   - Pilni rezultatai: `freqtrade_ranking.md` ir `freqtrade_all_results.csv`.
2. **„Sukčiavimo“ patikra** (`lookahead-analysis` + `recursive-analysis`) geriausioms 7 strategijoms. Logai: `validation/`.

## Atrinktos strategijos

Iš 1000 USDT po 5 metų. „Pirkti ir laikyti“ duotų: altcoin'ai **620**, BTC+ETH **790**.

| Strategija | Grupė | Tipas | Realiai %/m. | Iš viso | 2026 | Max kritimas | Patikra |
|---|---|---|---|---|---|---|---|
| CombinedBinHAndCluc | altcoin'ai | day trading, 5m | +9,1 | +54,6% | +7,5% | 14,6% | ✅ švari |
| ReinforcedAverageStrategy | altcoin'ai | swing, 4h | +6,5 | +36,9% | −11,8% | 27,5% | ✅ švari |
| Low_BB | altcoin'ai | swing, 1m | +6,3 | +35,4% | +2,0% | 10,4%* | ✅ švari |
| VolatilitySystem (futures) | BTC+ETH | swing, 1h | +69,8 | +1311% | −0,2% | 53,4% | ✅ švari, bet labai rizikinga (2x svertas, be stop-loss) |
| UniversalMACD | BTC+ETH | swing, 5m | +1,3 | +6,9% | +14,0% | 41,8% | ✅ švari |
| BinHV45 | BTC+ETH | day trading, 1m | +1,1 | +5,7% | +1,9% | 5,3% | ✅ švari |
| ~~NostalgiaForInfinityX8~~ | altcoin'ai | swing, 5m | ~~+14,7~~ | ~~+98,5%~~ | | | ❌ **naudoja ateities duomenis** |

\* testuota kiekvieniems metams atskirai, todėl realus kritimas gali būti didesnis.

### NostalgiaForInfinityX8 atmesta
`lookahead-analysis` du kartus rado, kad dalis išėjimo signalų naudoja ateities duomenis:
- 2025 m. pirmas pusmetis, SOL/XRP/DOGE: 4 iš 18 signalų;
- 2025 m., 10 altcoin'ų: 6 iš 20 signalų.

Todėl jos backtest rezultatas (+14,7%/m.) greičiausiai per geras. Tikroje prekyboje taip nebūtų.

## Nepadaryta: reikia tavo sprendimo
Surinkau **469 papildomas strategijas** iš kitų GitHub rinkinių. Jos guli `freqtrade/user_data/strategies/extra/`:
- keithorange/HUGE_FreqTrade_Strategy_Collection
- TheoBrigitte/freqtrade
- i1ya/freqtrade-strategies
- darkvolg/trendrider-strategy

**Nė vienos nepaleidau.** Tai nepatikrintas kodas iš nežinomų autorių, ir Claude Code saugumo filtras jų paleidimą sustabdė. Kodą tik perskaičiau, nepaleisdamas:
- Interneto, failų rašymo ar užšifruoto kodo nerasta.
- `Ichi.py` paleidžia sistemos komandą `rm` (trina savo log failą).
- `Uptrend.py` naudoja `eval()`.

**Variantai:**
- (a) Paleisti jas, jei leisi. Saugiausia būtų atskirame Docker konteineryje be interneto.
- (b) Testuoti tik žinomų autorių strategijas.

## Siūlomi kiti žingsniai
1. **Dry-run:** 2–3 švarias strategijas paleisti demo režimu 1–2 mėn. Siūlyčiau CombinedBinHAndCluc, Low_BB ir ReinforcedAverageStrategy ant altcoin'ų.
2. **VolatilitySystem:** įdomi, bet su svertu ir be stop-loss. Prieš bet kokį naudojimą reikėtų išbandyti saugesnę versiją, pvz. be sverto.
3. **Kiti įrankiai:** pereiti prie kitų įrankių aplankų. Kitas logiškas žingsnis: QuantConnect Lean akcijoms per IBKR.

## OctoBot (2026-11-09)
Pilna lentelė: `octobot_ranking.md`. 7 OctoBot robotai, OctoBot backtesteris, tos pačios taisyklės.
- BTC+ETH: Staggered Orders +10,2 %/m. (1626), Grid +7,0 %/m. (1401), Trailing Grid +5,2 %/m. (1290). Bet max kritimas 65–73 %, beveik kaip pirkti ir laikyti.
- Altcoin'ai: **visi pralaimi** „pirkti ir laikyti“. Grid tipo robotai prarado 86–90 %.
- Papildomai 11 Daily Trading versijų su atskirais indikatoriais: nė viena neuždirbo per 5 m. Geriausia DeathAndGoldenCross (BTC+ETH 941, alts 841, abu virš „pirkti ir laikyti“, bet vis tiek nuostolis).
- Išvada: OctoBot robotai nėra geresni už Freqtrade atrinktas strategijas. Grid tinka tik BTC+ETH ir tik su didele rizika.

## QuantConnect (2026-11-09)
Pilna lentelė: `quantconnect_ranking.md`. SPY „pirkti ir laikyti“: 1676 (+10,9 %/m., kritimas 24,5 %).
- SPY aplenkė tik 2: CAPM Dow 30 (valandinė 1954, bet kritimas 59 %) ir January Barometer (1931, kritimas 19 %, tik 6 sandoriai per 5 m.).
- Asset Class Momentum 1617 (kritimas 32 %), beveik kaip SPY.
- Kitos ~30 paleidimų: mažiau nei SPY, daug nuostolingų.

## 2026-11-11: `extra/` partijos (batch50–batch50f, ~300 iš 469)
- Iš `extra/` atrinkti tik EI3v2 ir E0V1E_DCA3 (žr. `best_strategies/ATRINKTI_BOTAI.md`). batch50d–f naujų nedavė: geriausios ClucHAnix_5m +16,4 %/m. (bet 2025 −10,6 %), CombinedBinHAndClucV5Hyperoptable +10,8 %/m.
- 1m strategijos ant 10 altcoin'ų netestuotos (reikia > 10 GB RAM). Kitą partiją sudaro `freqtrade/make_batch.py batch50g`.
- 2026-11-11 batch50g: **NASOSv5_mod3** atrinkta (alts10 +18,3 %/m., kritimas 3,3 %, nematytame 2018–21 +89 %/m.) → `best_strategies/ATRINKTI_BOTAI.md` nr. 3.
- 2026-11-12 batchM8: **ckNSJT_morning** atrinkta (alts10 5m +21,2 %/m., su 0,15 % mokesčiu +19 %, 2018–21 +90 %/m.; 2022 −14 %, balanso kritimas 37 %) → nr. 4. Ichimoku_v2/v5/v8/v16 – rizikingų sąraše.

## 2026-11-12: Instagram įrašų patikra
Atmesta: nakties dėžės pusė, Kronos (nepaleistas, laukia vartotojo), day-trader-skill (ORB), 8 trailing stop būdai, efektyvi riba, absorbcija.
**CE 50% Model (NQ) išlaikė:** 2016–2026 +0,115 R/sandorį, 10/11 metų pliuse, nematytas 2022–26 +17 %/m. prie 1 % rizikos, bet kritimas 25 %. Žadėta 59 %/m. neatsikartoja. → `tradingview/ce50/REZULTATAI.md`

## 2026-11-13: mokslinių straipsnių ir klasikinių sistemų patikra (`papers/EILE.md`)
- Atmesta (po paskelbimo pranašumo nėra): TSMOM ETF, žemas vol / BAB, PEAD, kripto porų prekyba, kripto valandų sezoniškumas, pre-FOMC, 52 sav. maksimumas, mėnesio sezoniškumas, liekamasis momentum, kripto žemas vol / MAX (funding suvalgo), Larry Williams VB, paprasti trendo filtrai.
- **Aberration atrinkta** (BTC+ETH 1d): +18,4 %/m., kritimas 28 %, 2018–21 +88 %/m.
- Potencialūs: Dual Thrust BTC+ETH (+11,7 %/m., kritimas 11 %, kasmet pliuse 2018–26; perp 0,05 % +13,8 %), R-Breaker (+15,2 % su 0,05 %), Turtle (+14 %, kritimas 30 %), volatilumu valdomas QQQ (kritimas 21 % vietoj 35 %).

- 2026-11-13 naktis (antras kompiuteris): straipsniai 25–33 (Connors, dienos vidaus momentum, KAMA/Supertrend/HMA, mėnesio sandūra, Crabel NR4/7, nakties grąžos, CME gap, BTC/altų rotacija) atmesti. **Funding kontrarinis** (BTC+ETH perp, long kai funding žemiau neutralaus) +26,5 %/m., kritimas 22 % – rizikingų sąraše (alts neveikia, 2025–26 silpsta), `FundingContrarian.py`. 1m detalumas: ckNSJT išlaiko, EI3v2 −¼ (~21 %/m.), E0V1E_DCA3 −⅓ (~12 %/m.).

- 2026-11-14 naktis (antras kompiuteris): **Passivbot trailing martingale atrinkta (nr. 11)**: 12 monetų futures, ekspozicija 0,75 – 2021–26 +21 %/m., kritimas 25 %, nematytas 2019-12 – 2021-04 +70 %/m.; jautrumas ir 2021 top 20 (su FTT) patikros praeina (`passivbot/REZULTATAI.md`). **Dry-run (šis kompiuteris, 7 botai, `freqtrade/dryrun/`)**: Aberration, DualThrust, EMA800, FundingContrarian, NASOSv5_mod3, EI3v2, FearGreedTrend. Fear & Greed trendas (FGI > 60) +23 %/m. – rizikingų sąraše. Straipsniai 34–51 atmesti. abbas/NASMAO/SMAO išlaiko 1m detalumą.
