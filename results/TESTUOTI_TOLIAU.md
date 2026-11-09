# Ką verta testuoti toliau (2026-11-09)

Atnaujinta po Freqtrade, OctoBot ir QuantConnect testų. Taisyklės tos pačios: 2021-11-08 – 2026-11-08, 1000 pradžia, 0,1 % mokestis, lyginti su „pirkti ir laikyti“.

## 1. Pirmiausia: patikrinti dvi geriausias (jau rastas)

| Strategija | Kodėl | Ką padaryti |
|---|---|---|
| CombinedBinHAndCluc (Freqtrade, altcoin'ai) | +9,1 %/m., kritimas 15 %, švari | Nematytas laikotarpis 2018–2021, tada dry-run |
| In & Out TQQQ/TMF (QuantConnect forumas) | +13,1 %/m., kritimas 31 %, 2022 +35 % | Ištaisyti svorių klaidą, nematytas 2015–2021, valandinės IBKR kainos |
Daugiau: `best_strategies/README.md`.

## 2. Labiausiai verta: 25 ETF strategijos (akcijos, IBKR)

Kodėl: aiškios paskelbtos taisyklės, mažai sandorių (kartą per mėnesį), užtenka nemokamų dienos kainų, lengva paleisti per IBKR. Testuoti Lean (kaip QuantConnect).

| # | Strategija | ETF | Taisyklė |
|---|---|---|---|
| 1 | GEM Dual Momentum (Antonacci) | SPY, EFA, AGG | Kas mėnesį: jei SPY 12 mėn. grąža > T-bill, laiko geresnį iš SPY/EFA, kitaip obligacijas AGG. |
| 2 | Accelerating Dual Momentum | SPY, SCZ, TLT | Kaip GEM, bet 1+3+6 mėn. grąžų vidurkis; greitesnė reakcija. |
| 3 | Composite Dual Momentum | 8 ETF poros (akcijos, REIT, kredito, ilgalaikės obligacijos, auksas) | Dual momentum kiekvienoje turto klasėje atskirai. |
| 4 | VAA-G4 (Keller) | SPY, EFA, EEM, AGG + LQD, IEF, SHY | 13612W momentum; jei bent vienas puolamasis neigiamas, eina į geriausią gynybinį. |
| 5 | VAA-G12 (Keller) | 12 ETF + 3 gynybiniai | Ta pati logika, platesnis krepšelis, laiko top 2. |
| 6 | DAA (Keller) | Kanarėlės VWO, BND; 12 ETF | Grynųjų dalis pagal tai, kiek „kanarėlių“ neigiamos. |
| 7 | BAA-G4 / BAA-G12 (Keller) | QQQ, EEM, EFA, AGG / 12 ETF; kanarėlės SPY, VWO, VEA, BND | Lėtas santykinis + greitas absoliutus momentum. |
| 8 | PAA (Keller) | 12 ETF | Apsauga pagal „breadth“: kiek ETF virš 12 mėn. vidurkio. |
| 9 | HAA (Hybrid Asset Allocation) | 8 ETF, kanarėlė TIP | Jei TIP momentum neigiamas, gynyba. |
| 10 | GTAA5 (Faber) | SPY, EFA, IEF, VNQ, DBC | Kiekvienas ETF laikomas tik jei virš 10 mėn. vidurkio, kitaip grynieji. |
| 11 | GTAA13 / Ivy Portfolio | 13 ETF | Ta pati 10 mėn. vidurkio taisyklė, platesnis krepšelis. |
| 12 | Generalized Protective Momentum | 12 ETF | Momentum + koreliacija, apsauga per breadth. |
| 13 | Adaptive Asset Allocation | 10 ETF | Top 5 pagal 6 mėn. momentum, svoriai pagal mažiausią svyravimą. |
| 14 | Kipnis Defensive Adaptive (KDA) | 10 ETF + kanarėlės | Momentum + minimalus svyravimas + kanarėlių apsauga. |
| 15 | Robust Asset Allocation | 7 ETF | Trend + momentum filtrai, pusė portfelio gali eiti į grynuosius. |
| 16 | Lethargic Asset Allocation | SPY, IWD, GLD, IEF + nedarbo lygis | Pasyvus, bet perjungia pagal nedarbą ir SPY trendą (reikia nedarbo duomenų). |
| 17 | Permanent Portfolio | SPY, TLT, GLD, SHY po 25 % | Kasmetinis perbalansavimas, be signalų. |
| 18 | All Weather (Dalio) | SPY 30 %, TLT 40 %, IEF 15 %, GLD 7,5 %, DBC 7,5 % | Kasmetinis perbalansavimas. |
| 19 | Golden Butterfly | SPY, IWN, TLT, SHY, GLD po 20 % | Kasmetinis perbalansavimas. |
| 20 | HedgeFundie UPRO/TMF 55/45 | UPRO, TMF | 3x sverto akcijos + 3x obligacijos, perbalansavimas kas ketvirtį. Labai rizikinga. |
| 21 | SPY 200 dienų vidurkio taisyklė | SPY, SHY | Laiko SPY, kai virš 200 d. vidurkio, kitaip grynieji. |
| 22 | TQQQ 200 dienų vidurkio taisyklė | TQQQ, QQQ signalas | Laiko TQQQ, kai QQQ virš 200 d. vidurkio. Labai rizikinga. |
| 23 | Sell in May | SPY | Laiko SPY lapkr.–bal., kitaip grynieji. |
| 24 | Canary momentum su apsauga (CXO) | SPY, VEA, VWO, BND | Kanarėlių apsauga daugiaklasiam momentum. |
| 25 | Sector rotation 12-1 momentum | 9 XL* sektorių ETF | Top 3 sektoriai pagal 12 mėn. (be paskutinio) momentum. |

## 3. Verta: 179 naujos Freqtrade strategijos (kripto)

Kodėl: tas pats testavimas kaip pirmųjų 65, viskas jau paruošta. Rizika: nežinomi autoriai, paleisti tik Docker be interneto. Po testo: `lookahead-analysis` geriausioms.
Kur: `freqtrade/sources_more/<rinkinys>/` (į GitHub neįkelta, atsisiųsti iš naujo pagal sąrašą žemiau).

### nateemma/strategies (64)

- AO (`SimpleStrategies/AO.py`)
- APO (`SimpleStrategies/APO.py`)
- Aroon (`SimpleStrategies/Aroon.py`)
- BBBreakout (`SimpleStrategies/BBBreakout.py`)
- BBRevert (`SimpleStrategies/BBRevert.py`)
- BOP (`SimpleStrategies/BOP.py`)
- BasketStrategy (`Basket/BasketStrategy.py`)
- BuyRegions (`TSPredict/BuyRegions.py`)
- CCI (`SimpleStrategies/CCI.py`)
- CMF (`SimpleStrategies/CMF.py`)
- CMO (`SimpleStrategies/CMO.py`)
- COPP (`SimpleStrategies/COPP.py`)
- Combo (`SimpleStrategies/Combo.py`)
- DCBreakout (`SimpleStrategies/DCBreakout.py`)
- DCRevert (`SimpleStrategies/DCRevert.py`)
- DYMI (`SimpleStrategies/DYMI.py`)
- DebugNNMTStrategy (`Debug/DebugNNMTStrategy.py`)
- EFI (`SimpleStrategies/EFI.py`)
- EMACross (`SimpleStrategies/EMACross.py`)
- EMV (`SimpleStrategies/EMV.py`)
- EWO (`SimpleStrategies/EWO.py`)
- EhlersBase (`SimpleStrategies/EhlersBase.py`)
- FVE (`SimpleStrategies/FVE.py`)
- FundingCarry (`Funding/FundingCarry.py`)
- HTSINE (`SimpleStrategies/HTSINE.py`)
- HTTREND (`SimpleStrategies/HTTREND.py`)
- KCBreakout (`SimpleStrategies/KCBreakout.py`)
- KCRevert (`SimpleStrategies/KCRevert.py`)
- KST (`SimpleStrategies/KST.py`)
- LWBreakout (`SimpleStrategies/LWBreakout.py`)
- LWRevert (`SimpleStrategies/LWRevert.py`)
- MACDhist (`SimpleStrategies/MACDhist.py`)
- MACDsignal (`SimpleStrategies/MACDsignal.py`)
- MI (`SimpleStrategies/MI.py`)
- MomentumRegimeBasket (`Basket/MomentumRegimeBasket.py`)
- MomentumRegimeBasket15m (`Basket/MomentumRegimeBasket15m.py`)
- NostalgiaForInfinityX (`reference/NostalgiaForInfinityX.py`)
- OversoldReversion (`Reversion/OversoldReversion.py`)
- PPO (`SimpleStrategies/PPO.py`)
- PSAR (`SimpleStrategies/PSAR.py`)
- PVO (`SimpleStrategies/PVO.py`)
- PZO (`SimpleStrategies/PZO.py`)
- ROC (`SimpleStrategies/ROC.py`)
- RVOL (`SimpleStrategies/RVOL.py`)
- SAR (`SimpleStrategies/SAR.py`)
- SMACross (`SimpleStrategies/SMACross.py`)
- STC (`SimpleStrategies/STC.py`)
- STOCHRSI (`SimpleStrategies/STOCHRSI.py`)
- TEMACross (`SimpleStrategies/TEMACross.py`)
- TRIX (`SimpleStrategies/TRIX.py`)
- TSI (`SimpleStrategies/TSI.py`)
- TSPredict (`TSPredict/TSPredict.py`)
- TS_ForecastPlot (`TSPredict/TS_ForecastPlot.py`)
- UO (`SimpleStrategies/UO.py`)
- VBM (`SimpleStrategies/VBM.py`)
- VFI (`SimpleStrategies/VFI.py`)
- VORTEX (`SimpleStrategies/VORTEX.py`)
- VZO (`SimpleStrategies/VZO.py`)
- WFRACTAL (`SimpleStrategies/WFRACTAL.py`)
- WILLR (`SimpleStrategies/WILLR.py`)
- WOBV (`SimpleStrategies/WOBV.py`)
- WTO (`SimpleStrategies/WTO.py`)
- ZLEMACross (`SimpleStrategies/ZLEMACross.py`)
- ZScore (`SimpleStrategies/ZScore.py`)

### werkkrew/freqtrade-strategies (42)

- ClucCrypROI (`strategies/archived/ClucCrypROI.py`)
- ClucCrypROI_BTC (`strategies/archived/ClucCrypROI.py`)
- ClucCrypROI_ETH (`strategies/archived/ClucCrypROI.py`)
- ClucCrypSlow (`strategies/archived/ClucCrypSlow.py`)
- ClucCrypSlow_BTC (`strategies/archived/ClucCrypSlow.py`)
- ClucCrypSlow_ETH (`strategies/archived/ClucCrypSlow.py`)
- Cluckie (`strategies/archived/Cluckie.py`)
- Enchilada (`strategies/archived/Enchilada.py`)
- Enchilada_Slow (`strategies/archived/Enchilada.py`)
- Hacklemore (`strategies/archived/HacklemoreX.py`)
- Hacklemore_Slow (`strategies/archived/Hacklemore.py`)
- Hacklemost (`strategies/archived/Hacklemost.py`)
- KAMACCIRSI_new (`strategies/archived/KAMACCIRSI.py`)
- Lateralus (`strategies/archived/Lateralus.py`)
- Lateralus_Slow (`strategies/archived/Lateralus.py`)
- Pmax (`strategies/archived/Pmax.py`)
- RenkoYolo (`strategies/archived/RenkoYolo.py`)
- Schism6_BTC (`strategies/archived/Schism-v1.6.py`)
- Schism6_ETH (`strategies/archived/Schism-v1.6.py`)
- Schism_BTC (`strategies/archived/Schism-0318.py`)
- Schism_ETH (`strategies/archived/Schism-0318.py`)
- Solipsis (`strategies/archived/Solipsis-v2.py`)
- Solipsis3 (`strategies/archived/Solipsis_v3.py`)
- Solipsis3_BTC (`strategies/archived/Solipsis_v3.py`)
- Solipsis3_ETH (`strategies/archived/Solipsis_v3.py`)
- Solipsis4 (`strategies/archived/Solipsis_v4.py`)
- Solipsis4_BTC (`strategies/archived/Solipsis_v4.py`)
- Solipsis4_ETH (`strategies/archived/Solipsis_v4.py`)
- Solipsis5_BTC (`strategies/archived/Solipsis-v2.5.py`)
- Solipsis5_ETH (`strategies/archived/Solipsis-v2.5.py`)
- Solipsis6 (`strategies/archived/Solipsis-v2.6.py`)
- Solipsis6_BTC (`strategies/archived/Solipsis-v2.6.py`)
- Solipsis6_ETH (`strategies/archived/Solipsis-v2.6.py`)
- SolipsisCon (`strategies/archived/Solipsis-Con-v1.py`)
- SolipsisCon_BTC (`strategies/archived/Solipsis-Con-v1.py`)
- SolipsisMM (`strategies/archived/SolipsisMM.py`)
- SolipsisMM_BTC (`strategies/archived/SolipsisMM.py`)
- SolipsisMM_ETH (`strategies/archived/SolipsisMM.py`)
- Solipsis_BTC (`strategies/archived/Solipsis-v2.py`)
- Solipsis_ETH (`strategies/archived/Solipsis-v2.py`)
- gettinMoist (`strategies/archived/gettinMoist.py`)
- ichi (`strategies/archived/Ichis.py`)

### MunkeyBalls/freqtrade (21)

- FreqaiExampleHybridStrategy (`freqtrade/templates/FreqaiExampleHybridStrategy.py`)
- FreqaiExampleStrategy (`freqtrade/templates/FreqaiExampleStrategy.py`)
- InformativeDecoratorTest (`tests/strategy/strats/informative_decorator_strategy.py`)
- StrategyTestV2 (`tests/strategy/strats/strategy_test_v2.py`)
- StrategyTestV3 (`tests/strategy/strats/strategy_test_v3.py`)
- StrategyTestV3Futures (`tests/strategy/strats/strategy_test_v3.py`)
- TestStrategyImplementBuyTimeout (`tests/strategy/strats/broken_strats/broken_futures_strategies.py`)
- TestStrategyImplementCustomSell (`tests/strategy/strats/broken_strats/broken_futures_strategies.py`)
- TestStrategyImplementSellTimeout (`tests/strategy/strats/broken_strats/broken_futures_strategies.py`)
- TestStrategyLegacyV1 (`tests/strategy/strats/failing_strategy.py`)
- TestStrategyNoImplementSell (`tests/strategy/strats/broken_strats/broken_futures_strategies.py`)
- TestStrategyNoImplements (`tests/strategy/strats/broken_strats/broken_futures_strategies.py`)
- freqai_rl_test_strat (`tests/strategy/strats/freqai_rl_test_strat.py`)
- freqai_test_classifier (`tests/strategy/strats/freqai_test_classifier.py`)
- freqai_test_multimodel_classifier_strat (`tests/strategy/strats/freqai_test_multimodel_classifier_strat.py`)
- freqai_test_multimodel_strat (`tests/strategy/strats/freqai_test_multimodel_strat.py`)
- freqai_test_strat (`tests/strategy/strats/freqai_test_strat.py`)
- someStrategy (`tests/test_strategy_updater.py`)
- strategy_test_v3_recursive_issue (`tests/strategy/strats/strategy_test_v3_recursive_issue.py`)
- strategy_test_v3_with_lookahead_bias (`tests/strategy/strats/lookahead_bias/strategy_test_v3_with_lookahead_bias.py`)
- testClass (`tests/test_strategy_updater.py`)

### jilv220/freqtrade-stuff (11)

- BB_RPB_3c (`BB_RPB_3c_dca.py`)
- BB_RPB_3c_dca (`BB_RPB_3c_dca.py`)
- BB_RTR (`BB_RTR_dca.py`)
- BB_RTR_dca (`BB_RTR_dca.py`)
- ClucHAnix_BB_RPB (`ClucHAnix_BB_RPB.py`)
- NostalgiaForInfinityV7_SMA (`NostalgiaForInfinityV7_SMA.py`)
- RSIDivTirail (`RSIDivergence.py`)
- SafeCluc (`SafeCluc.py`)
- StarRise_dca (`StarRise.py`)
- YourStrat (`TrailingBuyStrat.py`)
- pmaxTest (`pmaxTest.py`)

### stash86/MultiMA_TSL (10)

- Cenderawasih_2 (`user_data/strategies/Cenderawasih/Cenderawasih_2.py`)
- Cenderawasih_2_kucoin (`user_data/strategies/Cenderawasih_kucoin/Cenderawasih_2_kucoin.py`)
- Cenderawasih_3 (`user_data/strategies/Cenderawasih/Cenderawasih_3.py`)
- Cenderawasih_30m_1d (`user_data/strategies/Cenderawasih/Cenderawasih_30m_1d.py`)
- Matoa (`user_data/strategies/Matoa/Matoa.py`)
- MultiMA_TSL3b (`user_data/strategies/MultiMA_TSL.py`)
- MultiMA_TSL4b (`user_data/strategies/MultiMA_TSL/MultiMA_TSL4b.py`)
- MultiMA_TSL5 (`user_data/strategies/MultiMA_TSL/MultiMA_TSL5.py`)
- template (`user_data/strategies/template.py`)
- test_recursive (`user_data/strategies/samples/test_recursive.py`)

### phuchust/freqtrade_strategy (9)

- ClucHAnix_5M_E0V1E (`ClucHAnix_5M_E0V1E_DYNAMIC_TB.py`)
- ClucHAnix_5M_E0V1E_DYNAMIC_TB (`ClucHAnix_5M_E0V1E_DYNAMIC_TB.py`)
- NFI5MOHO_WIP (`NFI5MOHO_WIP.py`)
- NostalgiaForInfinityNext (`NostalgiaForInfinityNext_772SLMod.py`)
- NostalgiaForInfinityNext_ChangeToTower_V5_2 (`NostalgiaForInfinityNext_ChangeToTower_V5_2.py`)
- NostalgiaForInfinityNext_ChangeToTower_V5_3 (`NostalgiaForInfinityNext_ChangeToTower_V5_3.py`)
- NostalgiaForInfinityNext_ChangeToTower_V6 (`NostalgiaForInfinityNext_ChangeToTower_V6.py`)
- YourStratName (`Pump_detection_exemple.py`)
- bbandrsi (`bbandrsi.py`)

### ssssi/freqtrade_strs (8)

- BBMod (`binance/Archive/BBMod.py`)
- BinHV27F (`binance/Archive/BinHV27F.py`)
- BinHV27_short (`binance/Archive/BinHV27_short.py`)
- Cluc5mDCA (`ClucHAnix/ClucHAnix_5m.py`)
- ClucDCA (`ClucHAnix/ClucHAnix.py`)
- ConsensusShort (`binance/Archive/ConsensusShort.py`)
- E0V1EN (`binance/dry_run/E0V1EN.py`)
- HourBasedStrategy_5m (`binance/Archive/HourBasedStrategy.py`)

### brookmiles/freqtrade-stuff (8)

- EMA_Trailing_Stoploss (`strategies/examples/EMA_Trailing_Stoploss.py`)
- EMA_Trailing_Stoploss_LessMagic (`strategies/examples/EMA_Trailing_Stoploss_LessMagic.py`)
- Magic_Trailing_Stoploss (`strategies/examples/Magic_Trailing_Stoploss.py`)
- Obelisk_Ichimoku_Slow_v1 (`strategies/Obelisk_Ichimoku_Slow_v1.py`)
- Obelisk_Ichimoku_Slow_v1_1 (`strategies/Obelisk_Ichimoku_Slow_v1_1.py`)
- Obelisk_Ichimoku_Slow_v1_2 (`strategies/archive/Obelisk_Ichimoku_Slow_v1_2.py`)
- Obelisk_TradePro_Ichi_v2 (`strategies/archive/Obelisk_TradePro_Ichi_v2.py`)
- Obelisk_TradePro_Ichi_v2_2 (`strategies/archive/Obelisk_TradePro_Ichi_v2_2.py`)

### flightcom/freqtrade (4)

- Devil (`user_data/strategies/Devil.py`)
- HyperoptableStrategy (`tests/strategy/strats/hyperoptable_strategy.py`)
- TestStrategy (`user_data/strategies/test_strategy.py`)
- Zeus (`user_data/strategies/Zeus.py`)

### matthieu-hm/freqtrade_consumer_producer_strategies (1)

- DummyConsumerStrategy (`DummyConsumerStrategy.py`)

### hansen1015/freqtrade_strategy (1)

- NoLost (`NoLost.py`)

## 4. Galima pažiūrėti

- **Passivbot** (github.com/enarjord/passivbot): kripto grid/DCA robotas futures rinkai, turi savo backtesterį ir bendruomenės nustatymus. Grid OctoBot'e nepasiteisino, todėl žemas prioritetas.
- **Jesse pavyzdžiai** (11): Donchian, DUAL_THRUST, IFR2, KDJstrategy, MACD_EMA, MAGen, RSI2, SimpleBollinger, SMACrossover, TradingView_RSI, TurtleRules. Klasikinės idėjos, daugumą jau dengia Freqtrade/OctoBot. Reikia Jesse variklio.
- **Quantpedia nemokamos** (~70): akademinės strategijos, reikia nemokamos registracijos. Dalis reikalauja finansinių duomenų.
- **QuantConnect forumas**: dar šimtai temų. Skriptas jau yra: `quantconnect-lean/scripts/scrape_forum.py <temos id>`.

## Netestuoti (ir kodėl)

- Strategijos, kurioms reikia įmonių finansinių rodiklių, ateities sandorių, opcionų ar naujienų: nėra nemokamų duomenų (mokamas QuantConnect ~84 $/mėn.).
- Market making, arbitražas, signalų kopijavimas: nėra istorijos, kurią būtų galima testuoti.
- NostalgiaForInfinityX8: atmesta, naudoja ateities duomenis.