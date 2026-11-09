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

## Išvada
Veikia daug silpniau nei su kripto (+4 %/m. vietoj +25 %/m.). Kritimų ir atšokimų per mažai, o pelnas didžiąja dalimi iš 2025 m. Netinka.
