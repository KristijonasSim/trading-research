# Passivbot (github.com/enarjord/passivbot) – autoriaus pavyzdiniai konfigai, 2026-11-14
Docker atvaizdas `passivbot:stamped` (Rust plėtinys sukompiliuotas, pažymėtas šaltinio antspaudu). Binance USDT-M futures, 1 min. žvakės, maker 0,04 % / taker 0,055 % (konfigų numatyta), pradžia 100 000 USDT. Skriptai `run_bt*.sh`, suvestinė `summary.py` (iš `usd_total_equity`).

| Konfigas | Monetos | Ekspozicija (TWEL) | 2021-11 – 2026-11 | Kritimas | Nematytas 2019-12 – 2021-04 | Kritimas |
|---|---|---|---|---|---|---|
| btc_long (BTC užstatas, kaip autoriaus) | BTC | 4,36 | −45 %/m. | 95 % | — | — |
| btc_long (USDT užstatas) | BTC | 4,36 | +11 %/m. | 66 % | (2019-12 – 2021-11) −79 % | 99 % |
| BTC_ETH_XRP_SOL_ADA_long | 5 | autoriaus | +17 %/m. | 74–78 % | +176…+500 % | 50–56 % |
| default_trailing_martingale_long, autoriaus 40 monetų | 40 (šiandienos top – išgyvenusiųjų iškraipymas) | 1,5 | +108 %/m. | 78 % | — | — |
| **trailing martingale, 12 monetų (BTC, ETH + alts10)** | 12 | 1,5 | +48,8 %/m. | 51 % | +191 %/m. | 73 % |
| **ta pati** | 12 | **0,75** | **+21,1 %/m.** (kasmet pliuse: +5, +21, +23, +36, +13, +9) | **25 %** | **+69,8 %/m.** | 37 % |
| ema_anchor (long+short) | 12 | 2,5 / 2,5 | +38,3 %/m. (2025 −34 %) | 70 % | (2019-12 – 2021-11) +173 % | 41 % |
| hsl_npos1 (trailing martingale, 10 poz., stop pagal kritimą) | 12 | 1,25 | +14,7 %/m. (2022 −21 %) | 45 % | (2019-12 – 2021-11) +236 % | 36 % |
| ta pati | 12 | 0,4 | +11,3 %/m. | 14 % | (iki 2021-11) +35 % | 19 % |

Patikros (TWEL 0,75):
- Autorius optimizavo nuo 2021-04-20, todėl 2021–26 – jo kūrimo laikotarpis; tikrai nematytas 2019-12 – 2021-04: +69,8 %/m., kritimas 37 % (2020 m. +21 %, kai BTC +300 %).
- Su 0,1 % maker ir taker mokesčiu: +17,8 %/m., kritimas 26 %.
- Funding backteste neįskaičiuotas; įvertis (`funding_cost.py`, pozicija × funding istorija) ±1–2 % balanso per metus – vidutinė ekspozicija tik ~11 %, perka per kritimus, kai funding dažnai neigiamas.
- ⚠️ Martingale rizika: kritimuose dvigubina pozicijas (iki 0,75 balanso, be sverto virš 1x nėra likvidacijos). Kritimas nematytame periode 37 %.
- Jautrumas (2021–26 / nematytas 2019-12 – 2021-04): TWEL 1,0 → +30,7 %/m. (kritimas 34 %); TWEL 0,75 su 4 pozicijomis → +25,3 % (28 %) / +103 % (37 %); su 12 pozicijų → +16,9 % (16 %) / +51 % (37 %). Visi variantai pliuse kasmet arba beveik (2022 −1 %).
- Išgyvenusiųjų patikra: 2021-11 top 20 (su FTT, kuris žlugo 2022-11; LUNA futures duomenų Binance nebeturi, todėl 18 monetų): **+26,3 %/m., kritimas 24 %**, kasmet pliuse.
- ⚠️ **Kitos biržos duomenys (Bybit 1m, 2021-11 – 2026-11, ta pati konfigūracija): +11,3 %/m., kritimas 31 %** (2021 −3, 2022 −21, 2023 +38, 2024 +30, 2025 +14, 2026 +9). Skirtumas daugiausia LTC (−7,5k vs +10,6k) ir LINK (−2,4k vs +16,2k): martingale rezultatas priklauso nuo konkrečių dagčių ir kainų kelio. Kadangi forward testas būtų Bybit, šis skaičius svarbesnis. `run_bt8.sh`.
- **Bybit, pozicijų skaičius (TWEL 0,75)**: 12 poz. **+14,6 %/m., kritimas 14 %** (2021 +2, 2022 +11, 2023 +15, 2024 +25, 2025 +14, 2026 +5); 7 poz. +11,3 % (31 %); 4 poz. +10,2 % (57 %, 2022 −45 %). 12 pozicijų versija stabili abiejose biržose (Binance +16,9 %, 16 %) – rekomenduojama demo. `run_bt9.sh`.
- Kiti konfigai atmesti: btc_long sunaikina sąskaitą, 5 monetų – kritimai 74–78 %, ema_anchor – 70 %, hsl_npos1 – 45 %.

## Forward testas
Passivbot neturi popierinės prekybos („fake live“ – tik offline scenarijų testai). Dry-run galimas tik per biržos demo paskyrą (pvz., Bybit demo su `custom_endpoints.json`); raktai – kitame kompiuteryje (`~/trading/bybit_demo/`), reikia vartotojo sprendimo.
