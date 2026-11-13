# #32 Funding rate kaip kontrarinis signalas (BTC/ETH perp) – ⚠️ tik BTC+ETH, rizikinga
Long perp tik kai N d. vidutinis funding mažesnis už slenkstį (žemiau neutralaus 0,03 %/d. = pesimizmas), kitu metu be pozicijos. Funding mokėjimai ir 0,05 % mokestis įskaičiuoti, signalas vakar dienos.
- BTC+ETH N=3, slenkstis 0,01 %/d.: 2020–21 +31 %/m. (kritimas 16 %), 2021–26 **+26 %/m., kritimas 30 %**; rinkoje ~30 % laiko, ~90 įėjimų per 5 m. kiekvienai monetai. Su 0,1 % mokesčiu +24 % (BTC) / +20 % (ETH).
- Jautrumas (`REZULTATAI_jautrumas.txt`): N 1–5 ir slenkstis 0,005–0,015 %/d. → 2021–26 +13…+26 %/m.; arčiau neutralaus (≥ 0,025) arba ilgesnis N (≥ 14) → minusas. Parametrus renkantis tik iš 2020–21 (geriausias N=1, 0,015) 2021–26 gaunasi +22 %/m.
- ⚠️ Ant alts10 su tais pačiais parametrais neveikia: 2021–26 −11…+5 %/m., kritimai 41–62 % (`REZULTATAI_alts.txt`). ETH 2020–21 tik +3,6 %/m. Viską neša BTC.
- Variantai B (laikyti visada, išeiti per perkaitimą) ir C (short per perkaitimą) – 2021–26 visi minuse.
Išvada: įdomu, bet patvirtina tik BTC. Reikėtų freqtrade versijos (funding duomenys) ir dry-run, kol kas rizikingų sąraše.

## Freqtrade patikra (2026-11-13)
`freqtrade/user_data/strategies/papers/FundingContrarian.py` (futures, 0,05 %, funding įskaičiuotas variklio), BTC+ETH 2021-11 – 2026-11:
- **CAGR +26,5 %, kritimas 21,9 %**, 183 sandoriai (sutampa su pandas). Metai: 2022 +656 USDT (PF 1,86), 2023 +814 (4,37), 2024 +431 (4,69), 2025 +305 (1,21), 2026 +38 (1,05) – pranašumas silpsta.
- Lookahead: 0/20 įėjimo ir išėjimo signalų paveikta; pažymėtas tik indikatorius `fsum` – paskutinės žvakės dienos funding suma (00, 08, 16 val. mokėjimai žinomi iki dienos uždarymo 24:00), t. y. patikros artefaktas.
- Su +1 d. vėlavimu (`FundingContrarianLag.py`): +15,6 %/m., kritimas 27 % – signalas sensta per dieną, reikia vykdyti iškart 00:00 UTC.
