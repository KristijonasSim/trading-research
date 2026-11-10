# Dienos prekyba / scalping ant indeksų (2026-11-10)

Duomenys: Dukascopy 5m CFD (NAS100 = USATECH.IDX, SPX500, US30), 2021-03 – 2026-11, tik 9:30–16:00 NY, 1x be sverto.
Skriptai: `sim.py` (EI3v2 indikatoriaus kopija), `grid.py`, `intraday.py`, `extra.py`. Duomenys nesaugomi repo (`fetch_idx.py` scratchpad'e, žr. PROGRESS).

| Strategija | Rinka | %/m. | Kritimas | 2025–2026 | Išvada |
|---|---|---|---|---|---|
| Laikyti | NAS100 | 14,2 | 37,6 % | | atskaita |
| Laikyti | SPX500 | 12,5 | 27,4 % | | atskaita |
| EI3v2 (auto mastelis, kaip indikatorius) | NAS100 5m | −2,4 | 25 % | −0,8 | netinka |
| EI3v2 geriausias iš 480 variantų | NAS100 5m | 3,4 | 5,9 % | 3,1 | per silpna |
| ORB 5m (Zarattini & Aziz 2023) | NAS100 | 2,9 | 14,7 % | 0,4 | netinka |
| Intraday momentum (Gao ir kt. 2018) | visi | −7…−9 | 33–42 % | neigiama | netinka |
| **Noise Breakout (Zarattini, Aziz, Barbon 2024)** | **NAS100** | **12,0** | **10,2 %** | **6,2** | **geriausia** |
| Noise Breakout | SPX500 | 5,5 | 11 % | −1,0 | silpna |
| Noise Breakout | US30 | −2,2 | 17 % | −3,2 | netinka |

Noise Breakout NAS100, spread 0,003 % į pusę (Capital.com ~1,8 p.): 2021 +8,8, 2022 +25,4, 2023 +15,3, 2024 +8,2, 2025 +6,6, 2026 +5,0 %.
~1 sandoris per dieną, laimi 42 %, profit factor 1,31. Tik long: +8,2 %/m., kritimas 5,3 %.
**Labai jautri kaštams:** spread 0,01 % → +8,2 %/m.; 0,02 % → +3 %/m. Po paskelbimo (2025+) silpnesnė.
Parametrai paimti iš straipsnio, nederinti (nėra persimokymo rizikos iš mūsų pusės).

TradingView: `tradingview/Noise_Breakout_NAS100.pine`.

## Patobulinimai (noise2.py, 108 variantai; renkama pagal 2021–24, tikrinama 2025–26)
| Variantas | 2021–24 %/m | kritimas | PF | 2025–26 %/m | kritimas | PF |
|---|---|---|---|---|---|---|
| Straipsnis (kas 30 min.) | 14,9 | 4,6 | 1,38 | 6,2 | 10,2 | 1,17 |
| **Kas 60 min.** | 15,0 | 5,6 | 1,44 | **7,7** | **6,5** | 1,25 |
Trendo filtras (SMA 50/200), platesnės ribos (×1,25/1,5), tik VWAP stop: nepagerino. Tik long: 2025–26 silpna.
5 min. ir 15 min. grafikai duoda tą patį (sprendimai priimami tik kas valandą). Indikatoriuje numatyta kas 60 min.

## Atšokimo scalperis (RSI(2) + VWAP, `meanrev.py`, 24 variantai × NAS100/SPX500 × 5m/15m)
Laimi 55–60 % sandorių (atrodo „stabiliau“), bet visi geriausi variantai 2021–24 nuostolingi (−0,7…−3,7 %/m.), 2025–26 taip pat. Netinka.
Išvada: indeksuose dažnai laiminčios scalping strategijos po kaštų pralaimi; Noise Breakout (kas 60 min.) lieka geriausia.

## Kitos rinkos ir pozicijos dydis (`noise3.py`, `sizing.py`)
| Rinka (sesija) | kas 60 min. 2021–24 | 2025–26 | Išvada |
|---|---|---|---|
| NAS100 (9:30–16:00 NY) | +15,0 %/m., kritimas 5,6 % | +7,7 %, 6,5 % | geriausia |
| GER40 (9:00–17:30 Berlyno) | +4,5 %, 8,3 % | +4,2 %, 6,7 % | silpna |
| XAUUSD (NY 8:20–13:30 / Londonas 8:00–16:30) | ~0 % | ~0 % arba − | netinka |
Pozicijos dydis pagal svyravimą (tikslas 1–2 %/d., iki 1x/2x): rizikos ir grąžos santykio nepagerino.
