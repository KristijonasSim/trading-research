# Geriausias įrankis: Noise Breakout NAS100 (2026-11-10)

**Failas:** `tradingview/Noise_Breakout_NAS100.pine` (patikrinta TradingView, Pepperstone NAS100 15m: kompiliuojasi, rodo BUY/SELL, vieną SL ir vieną TP liniją, ✓/✗ rezultatą).
**Šaltinis:** Zarattini, Aziz, Barbon (2024), SSRN 4824172. Vienintelis pakeitimas: tikrinama kas 60 min. (ne 30).
**Grafikas:** NAS100, 15 min. (arba 5 min., rezultatas tas pats). Prekiauja tik 16:30–23:00 Lietuvos laiku, per naktį nelaiko.

## Rezultatai (Dukascopy NAS100 5m, spread 0,003 % į pusę, 1x)
| | %/m. | Kritimas | Laimi | Pelningi mėn. |
|---|---|---|---|---|
| 2021–2024 | +15,0 | 5,6 % | 48 % | 74 % |
| 2025–2026 (nematyta) | +7,7 | 6,5 % | 44 % | 61 % |
| Laikyti NAS100 2021–26 | +14,4 | 38 % | | |

## Kas išbandyta ir atmesta (~400 variantų)
| Idėja | Rezultatas |
|---|---|
| EI3v2 (kripto botas) ant NAS100, 480 variantų | geriausias +3 %/m. |
| ORB 5m (Zarattini & Aziz 2023) | +3 %/m., 2025+ ~0 |
| Intraday momentum (Gao ir kt. 2018) | −7…−9 %/m. |
| Atšokimo scalperis RSI(2)+VWAP, 24 var. × 2 rinkos × 2 grafikai | visi nuostolingi |
| Noise Breakout ant SPX500 / US30 / GER40 / aukso | +5 % / − / +4 % / ~0 |
| Trendo filtras, platesnės ribos, tik VWAP stop, dydis pagal svyravimą | nepagerino |
| QQQ3 (3x) kai QQQ > 200 d. vidurkis | 2011–26 puiku (+28 %/m.), bet 2000–10 −90 % → nesaugu (`qqq3_trend/REZULTATAI.md`) |

## Rizikos
- Labai jautri spread'ui: 0,01 % → +8 %/m. (2021–26), 0,02 % → +3 %/m. Naudoti brokerį su mažu NAS100 spread'u.
- 2025–26 silpnesnė nei anksčiau; TradingView istorijoje (2026 m.) ~0 %.
- Laimi < 50 % sandorių: dienos atrodo atsitiktinės, pranašumas matosi tik per mėnesius.
- Prieš tikrus pinigus: demo 1–2 mėn.
