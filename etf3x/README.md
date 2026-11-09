# Kripto botai ant 3x ETF (2026-11-09)

Ar atrinkti kripto botai (EI3v2_tag_cofi_green, E0V1E_DCA3) veikia su 3x sverto ETF?

## Duomenys
- 18 3x ETF atkurti iš 1x ETF 5m kainų (Dukascopy, JAV prekybos valandos): `fetch.py`, `build.py`.
  TQQQ, UPRO, UDOW, TNA, SOXL*, TECL, FAS, ERX, NUGT, JNUG, YINN, TMF, CURE, DRN, UTSL, EDC, DPST*, BRZU (* tik nuo 2024 pab.).
- Patikra: sintetinis TQQQ vs tikras 2021-11 – 2026-11: koreliacija 0,9994, abu ×1,29.
- Freqtrade, 2021-11-08 – 2026-11-08, mokestis 0,05 % į vieną pusę, BTC filtras pakeistas SPY (`strategies/`, `run.sh`).

## Rezultatai
| | %/m | Iš viso | Max kritimas | Sandorių/d. | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|
| EI3v2_tag_cofi_green | 4,0 | +21,5 % | 18,6 % | 0,9 | −7,0 | 8,4 | −1,2 | 25,6 | −2,0 |
| E0V1E_DCA3 | 3,5 | +18,7 % | 9,8 % | 0,9 | −1,0 | 1,3 | 3,3 | 2,7 | 11,4 |
| Laikyti UPRO (3x S&P500) | ~12 | ×1,79 | ~60 % | – | | | | | |
| Laikyti TQQQ | ~5 | ×1,29 | ~80 % | – | | | | | |

Geriausiai sekėsi aukso kasyklų fondams (NUGT, JNUG): jie juda kaip altcoin'ai.

## Didesni grafikai (strategijos timeframe pakeistas, stop'ai tikrinami 5m žvakėmis)
Be 5m detalumo rezultatai buvo per geri (pvz. EI3v2 1h +18,9 %/m.), nes siauras trailing stop ant didelių žvakių „parduoda“ geriausia kaina.

| Grafikas | EI3v2 %/m | kritimas | E0V1E_DCA3 %/m | kritimas |
|---|---|---|---|---|
| 5m | 4,0 | 18,6 % | 3,5 | 9,8 % |
| 1h | 12,1 | 12,4 % | 2,9 | 15,9 % |
| 4h | 7,3 | 11,4 % | −1,1 | 26,6 % |
| **1d** | **13,5** | 14,5 % | 8,3 | 14,3 % |

EI3v2 1d pagal metus: 2022 +12,9 %, 2023 +3,6 %, 2024 +15,0 %, 2025 +17,6 %, 2026 +6,1 % (visi teigiami, laimi 80 % sandorių).
Daugiausia pelno: JNUG, NUGT (aukso kasyklos), TQQQ, UPRO. Nuostolingi: YINN, UDOW, TMF.
Atsargiai: grafikas parinktas iš 4 bandytų, todėl dalis rezultato gali būti sėkmė. Strategijos failas `strategies_tf/`.

## Išvada
5m grafike netinka (+4 %/m.). Dienos grafike EI3v2 duoda +13,5 %/m., kasmet teigiama, kritimas 14,5 %: arti 14 % ribos, verta stebėti, bet į atrinktus nededama.
