# Trend Konsensusas (TradingView strategija), 2026-11-09

Kodas: vartotojo iškarpinėje; kopija `/tmp/.../scratchpad/tk.pine` (laikina).

## Kaip testuota
- 22 instrumentai dienos grafike (NAS100, S&P500, QQQ, SPY, DIA, IWM, auksas, sidabras, nafta, EUR/GBP/JPY, AAPL, MSFT, NVDA, AMZN, TSLA, META, GOOGL, XLE, BTC, ETH), 1h ir 4h kripto/žaliavos/valiutos.
- Mokestis + slydimas 0,07 % į vieną pusę. Įėjimas kitos žvakės atidarymu.
- Parametrai rinkti pirmuose 60 % duomenų, rezultatai iš likusių 40 % (nematytų).
- 8 žinomi metodai × ~100 nustatymų: SuperTrend, Donchian, Chandelier, EMA kirtimas, KAMA, momentum, RSI(2) Connors, SuperTrend+EMA200.

## Rezultatai (nematytas laikotarpis, medianos)
| Variantas (D) | Pelnas (log) | Max kritimas | Lenkia „pirkti ir laikyti“ |
|---|---|---|---|
| Pirkti ir laikyti | 1,25 | −50 % | – |
| Konsensusas 1x | 0,83 | −28 % | 18 % instr. |
| Konsensusas 1,5x | 1,15 | −40 % | 32 % |
| Konsensusas 2x | 1,39 | −50 % | 55 % |

4h (kripto, žaliavos, valiutos): konsensusas 0,32 vs pirkti ir laikyti 0,07, lenkia 45 %, kritimas −30 %.
1h: po mokesčių pranašumo nėra (−0,05 vs 0,07).
Short pusė visur blogino rezultatą. Ankstesnis „AI Be Atsilikimo“ kNN: 50 % atspėjimas (atsitiktinis) – atmestas.

## Išvada
Stebuklo nėra: trendo sistemos daugiausia mažina kritimus. Pelno daugiau už laikymą tik su ~2x svertu D grafike arba 4h grafike.

## TradingView patikra (NAS100 Capital.com, D, 2015-04 – 2026-11, 0,05 % mokestis)
- Kodas kompiliuojasi be klaidų.
- 1x: +244 %, max kritimas 13 %, pelno faktorius 4,4.
- 2x: +827 %, max kritimas 26 %, pelno faktorius 3,3.
- Pirkti ir laikyti: ~+527 %.

## Dienos prekyba (NQ ateities sandoriai kaip NAS100 pakaitalas, taisyklė BUY>=3/SELL<=1, spredas 1,8–4 p., finansavimas 6 %/m.)
| Rėmas | Tik long | Long+short | Laikant | Max kritimas (long) |
|---|---|---|---|---|
| 1h (2,4 m.) | +21 % | +3 % | +37 % | −18 % |
| 4h (2,4 m.) | 0 % | −34 % | +37 % | −19 % |
| 15m (2,3 mėn.) | −5,5 % | −5 % | −7 % | −9 % |
| 5m (2,3 mėn.) | −2 % | +3 % | −7 % | −8 % |
Išvada: dienos prekybai netinka. Short pusė visada blogina. 15m/5m duomenų tik 2 mėn.

## NAS100 D, paskutiniai 3 m. (2023-11-06 – 2026-11-06)
- Laikant (ETF, be finansavimo): +78 %, max kritimas −23 %. Indikatorius 1x: +70 %, −18 %.
- Per CFD su 6 %/m. finansavimu: laikant +48 %, indikatorius 1x +45 %, 2x +95 % (kritimas −34 %).
- 4 sandoriai, 3 pelningi. Metai: 2024 ir 2025 laikymas geresnis, 2026 indikatorius geresnis.

## Vartotojo idėja: po SELL, kai kaina pasiekia TP2 žemyn – iškart BUY (2026-11-09)
- NAS100 3 m.: dabar +70 %, su idėja +117 %, laikant +78 % (be finansavimo).
- 22 instr., nematytas laikotarpis: geriau nei dabartinė versija 77 % instrumentų, mediana 1,07 vs 0,84 (log), kritimas tas pats (−38 %).
- Išeiti ties TP2 viršuje – blogiau. Short nuo SELL iki TP2 – NAS100 +159 %, bet kituose nestabilu, kritimas −47 %.

## Trailing stop virš TP2 (2026-11-09)
- Bazė: B (BUY ties TP2 po SELL, laikyti iki SELL): NAS100 3 m. +117 %, 22 instr. mediana 1,07.
- Trailing 1,5–6 ATR be grįžimo: NAS100 +95–103 %, mediana ~0,5 (perpus blogiau).
- Trailing + grįžimas po naujo aukščiausio: NAS100 +97–110 %, mediana 0,94–1,06, geriau nei B tik 32–36 % instr.
- Išvada: nepagerina. SELL signalas pats veikia kaip trailing stop.

## Trailing tik toli virš TP2 (aktyvuoti TP2+2…10 ATR, trail 3…8 ATR, su/be grįžimo; 32 variantai)
- Geriausias pagal senesnius duomenis: TP2+10 ATR, trail 8 ATR + grįžti. Nematytame: mediana 1,05 vs B 1,07; geriau nei B 23 % instr.; NAS100 3 m. +105 % vs +117 %.
- Išvada: praktiškai tas pats kaip laikyti iki SELL, pranašumo nėra.

## Metinis pelnas, NAS100 D, variantas B (2026-11-09)
| Laikotarpis | Indikatorius | CFD su finans. | Laikant | Max kritimas |
|---|---|---|---|---|
| 41 m. | 11,9 % | ~6,9 % | 14,3 % | −73 % (2000–02) |
| 20 m. | 13,6 % | ~8,3 % | 14,7 % | −48 % |
| 10 m. | 22,5 % | ~17,1 % | 18,9 % | −25 % |
| 5 m. | 18,8 % | ~13,8 % | 10,6 % | −23 % |
| 3 m. | 29,5 % | ~24,1 % | 21,2 % | −17 % |
22 instr., 10 m. mediana: 14,3 % vs laikant 16,3 %. Pastaba: pirkimas ties TP2 ilgo kritimo metu (2000–02) didina nuostolius.

## 22 ETF / indeksai, variantas B (2026-11-09) → `results/trend_konsensusas_etf.csv`
- 10 m. laimi prieš laikymą 9/22: XLK, QQQ, NAS100, SPY, VTI, S&P500, EWJ, FXI, TLT. Visada mažesnis kritimas JAV indeksuose (−25 % vs −35 %).
- Pralaimi: SMH, ARKK, XBI, XLE, XLF, XLV, Europa, besivystančios. Tinka stipriai kylantiems JAV indeksams.
