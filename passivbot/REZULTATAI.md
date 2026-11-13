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
| ta pati | 12 | 0,4 | +11,3 %/m. | 14 % | (iki 2021-11) +35 % | 19 % |

Patikros (TWEL 0,75):
- Autorius optimizavo nuo 2021-04-20, todėl 2021–26 – jo kūrimo laikotarpis; tikrai nematytas 2019-12 – 2021-04: +69,8 %/m., kritimas 37 % (2020 m. +21 %, kai BTC +300 %).
- Su 0,1 % maker ir taker mokesčiu: +17,8 %/m., kritimas 26 %.
- Funding backteste neįskaičiuotas; įvertis (`funding_cost.py`, pozicija × funding istorija) ±1–2 % balanso per metus – vidutinė ekspozicija tik ~11 %, perka per kritimus, kai funding dažnai neigiamas.
- ⚠️ Martingale rizika: kritimuose dvigubina pozicijas (iki 0,75 balanso, be sverto virš 1x nėra likvidacijos). Kritimas nematytame periode 37 %.
- Išgyvenusiųjų patikra: 2021-11 top 20 (su FTT, kuris žlugo 2022-11; LUNA futures duomenų Binance nebeturi, todėl 18 monetų): **+26,3 %/m., kritimas 24 %**, kasmet pliuse.
- Kiti konfigai atmesti: btc_long sunaikina sąskaitą, 5 monetų – kritimai 74–78 %.
