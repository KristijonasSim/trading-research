# #18 Klasikinės Jesse pavyzdžių strategijos (Turtle, Dual Thrust) ant kripto – ⚠️ potencialios, žemiau 14 %/m. ribos

Binance spot dienos žvakės, tik long, kiekviena moneta po lygią dalį, mokestis 0,1 %. Skriptai `test.py`, `dt_check.py`, `dt_5m.py`; lentelės `REZULTATAI.txt`, `REZULTATAI_dualthrust.txt`.

| Grupė | Strategija | 2018–2021-11 %/m. (kritimas) | 2021-11–2026-11 %/m. (kritimas) |
|---|---|---|---|
| BTC+ETH | Laikyti | +63,9 (88 %) | −4,2 (76 %) |
| BTC+ETH | Turtle S1 (20/10, stop 2N) | +107,6 (33 %) | +14,1 (37 %) |
| BTC+ETH | Turtle S2 (55/20) | +73,8 (49 %) | +14,5 (30 %) |
| BTC+ETH | **Dual Thrust n=4, k=0,7** | +30,0 (8 %) | **+11,9 (11 %)** |
| alts10 | Laikyti | +177 (64 %) | −13,6 (80 %) |
| alts10 | Turtle S1 | +119,5 (27 %) | +10,4 (42 %) |
| alts10 | Dual Thrust k=0,7 | +37,2 (8 %) | +6,0 (20 %) |

**Dual Thrust BTC+ETH** (riba = dienos atidarymas + 0,7 × 4 d. diapazonas, įeinama stop orderiu dienos viduje, uždaroma dienos gale 00:00 UTC):
- Kiekvienais metais pliuse: 2018 +4, 2019 +27, 2020 +60, 2021 +30, 2022 +1, 2023 +14, 2024 +20, 2025 +17, 2026 +7 %. Rinkoje tik 11 % laiko.
- Parametrai stabilūs: n=4–6, k=0,5–0,8 → 2021–26 +7…12 %/m.
- 5m vykdymas (įėjimas pirmame 5m bare, pramušusiame ribą) duoda tą patį rezultatą: +11,9 %/m.
- ⚠️ Jautrus mokesčiui: su 0,15 % tik +7,5 %/m. (2022 −2 %). Reikia maker / žemo mokesčio (BNB nuolaida).

**Turtle BTC+ETH:** +14 %/m., bet kritimas 30–37 % ir 2022 m. −18…−24 %.

**Dual Thrust ant indeksų ir aukso** (SPY, QQQ, IWM, GLD, Yahoo dienos OHLC, mokestis 0,02 %, `dt_idx.py`): 2005–15 ir 2016–26 visi variantai −6…+1 %/m. Pranašumas yra tik kripto rinkoje (24 val. prekyba, stiprūs dienos trendai).

**Dual Thrust ant Binance perp BTC/ETH** (tik long, mokestis 0,05 % taker, su funding, `dt_perp.py`, `REZULTATAI_dt_perp.txt`):
- n=4, k=0,7: 2020–21 +38 %/m. (kritimas 18 %), **2021-11 – 2026-11 +13,8 %/m. (kritimas 12 %)**; metai 2020 +35, 2021 +35, 2022 +3, 2023 +15, 2024 +25, 2025 +17, 2026 +8 %.
- Su 0,02 % (maker) +16,6 %/m.
- Long+short (originali versija) blogiau: +5,6 %/m., kritimas 35 %. Short pusė kripto rinkoje neveikia.
- Su 2x svertu teoriškai ~+27 %/m., kritimas ~24 %. Kandidatas į dry-run.
