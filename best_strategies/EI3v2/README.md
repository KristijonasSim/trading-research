# EI3v2_tag_cofi_green: kripto botas (Freqtrade)

Strategija perka staigius altcoin'ų kainų kritimus 5 min. grafike ir parduoda atšokus. Laimi apie 94 % sandorių.
Autorius ne mes: [keithorange/HUGE_FreqTrade_Strategy_Collection](https://github.com/keithorange/HUGE_FreqTrade_Strategy_Collection).

## Rezultatai

Binance futures, 10 altcoin'ų (XRP, BNB, SOL, DOGE, ADA, TRX, LINK, AVAX, LTC, DOT), 2020-01 – 2026-11, mokestis 0,05 %, pradžia 1000 USDT, iki 10 sandorių vienu metu.

| Svertas | Per metus (vid.) | Didžiausias kritimas | Ar tinka |
|---|---|---|---|
| 1x | +81 % | 17 % | ✅ saugiausia |
| 2x | +210 % | 49 % | ✅ |
| 2,4x | +267 % | 50 % | ⚠️ pati riba |
| 2,5x | +272 % | 60 % | ❌ |
| 3x | +276 % | 94 % | ❌ |

### Pagal metus

| Metai | 1x | 2x | 2,4x |
|---|---|---|---|
| 2020 | +60 % | +88 % | +151 % |
| 2021 | +911 % | +10 090 % | +14 252 % |
| 2022 | +33 % | +76 % | +98 % |
| 2023 | +27 % | +66 % | +82 % |
| 2024 | +66 % | +154 % | +211 % |
| 2025 | +20 % | +48 % | +59 % |
| 2026 (iki 11-08) | +4 % | +10 % | +13 % |

Altcoin'ų „pirkti ir laikyti“: 2022 −67 %, 2025 −34 %, 2026 −30 %. Strategija pliuse visus metus.

## Ką reikia žinoti

- **Pelnas priklauso nuo to, kiek rinka svyruoja, ne nuo kainų krypties.** 2022 m. kainos krito 67 %, strategija uždirbo +33 % (1x). 2026 m. rinka rami, sandorių 5 kartus mažiau, todėl tik +4 %.
- **2021 m. skaičiai nerealūs:** perinvestuojant pelną susidaro milijonai, o tokių sandorių rinka nepriimtų. Tikėtis verta panašiai kaip 2023–2026 m.
- **Nėra stop-loss** (−99 %): vienas didelis kritimas su svertu gali kainuoti daug.
- Svertas 2021–26 atrodė saugus iki 3x, bet pridėjus 2020–21 m. riba nukrito iki ~2,4x.
- Ne kripto rinkose (auksas, NAS100, S&P 500) neveikia.
- Patikrinta: nenaudoja ateities duomenų (Freqtrade `lookahead-analysis`), išlaikė nematytą 2018–21 (spot, be sverto).

## Failai

| Failas | Kas jame |
|---|---|
| `EI3v2_tag_cofi_green.py` | Originali strategija (1x) |
| `levwrap.py`, `EI3v2_tag_cofi_green_Lev.py` | Sverto versija: svertas iš kintamojo `LEV` |
| `config_futures_market.json` | Testo nustatymai |

Paleisti testą (iš `freqtrade/`, failai `user_data/strategies/lev/`):

```bash
LEV=2 freqtrade backtesting -c config_futures_market.json -s EI3v2_tag_cofi_green_Lev \
  --strategy-path user_data/strategies/lev --timerange 20200101-20261108 \
  -p XRP/USDT:USDT BNB/USDT:USDT SOL/USDT:USDT DOGE/USDT:USDT ADA/USDT:USDT TRX/USDT:USDT \
     LINK/USDT:USDT AVAX/USDT:USDT LTC/USDT:USDT DOT/USDT:USDT --breakdown year
```

Kitas žingsnis: dry-run / demo 1–2 mėn. Visų sverto testų detalės: `freqtrade/results/lev3/REZULTATAI.md`.
