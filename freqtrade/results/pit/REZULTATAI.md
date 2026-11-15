# Išgyvenusiųjų patikra: 2021-11 top 20 (be BTC/ETH), įskaitant LUNA (iki žlugimo) ir FTT
Freqtrade 2021-11-08 – 2026-11-08, 5m, be detalumo, max 18 pozicijų; MATIC duomenys iki 2024-09. Skriptai `pit_fetch.py`, `pit_bt.sh`.

| Strategija | alts10 (dabartinės) | 2021-11 top 20 | Pastaba |
|---|---|---|---|
| EI3v2_tag_cofi_green | +25,1 %/m., kritimas 14,9 % | **+29,2 %/m.**, kritimas 17 % (balanso 28 %) | ✅ išlaiko; FTT +584 USDT, LUNA −21 |
| NASOSv5_mod3 | +18,3 %, 3,3 % | **+15,5 %**, balanso 15,7 % | ✅ išlaiko, bet LUNA −202 USDT, 2022 −39 USDT |
| E0V1E_DCA3 | +17,1 %, 6,5 % | **+15,3 %**, balanso 23 % | ✅ išlaiko; blogiausi ATOM 2025-10-10 −99 %, LUNA −99 % |
| ckNSJT_morning | +21,2 %, 17,2 % (balanso 37 %) | **+19,4 %**, balanso 39,6 % | ✅ išlaiko grąžą, kritimas didelis (market orderiai, `config_spot_market.json`) |
| NASMAO | +18,2 %, 16,2 % | **+14,2 %**, balanso 39,2 % | ⚠️ grąža −4 p. p., kritimas dvigubai didesnis |
| abbas | +14,2 %, 8,7 % | **+10,1 %**, balanso 33,2 % | ⚠️ krenta žemiau 14 % ribos |
| SMAO | +15,1 %, 31,4 % | **+9,9 %**, balanso 40,4 % | ❌ silpna su tuometinėmis monetomis |

| EI3v2_tag_cofi_green_2_4 | +27,1 %, 8,6 % | **+36,0 %**, balanso 29,9 % | ✅ išlaiko (geriausia) |
| BSS2b | +21,9 %, 16,3 % | **+30,9 %**, balanso 44,8 % | ✅ grąža išlaiko, kritimas didelis |
| EI3v2_tag_cofi_green_7 | +25,6 %, 15 % | **+29,3 %**, balanso 34,1 % | ✅ išlaiko |
| DS_Green_5m | +26,6 %, 6,7 % | **+19,8 %**, balanso 26,9 % | ✅ išlaiko, −7 p. p. |
| BearBull3 | +15,5 %, 9,4 % | **+15,3 %**, balanso 10,3 % | ✅ išlaiko, mažiausias kritimas |
| KeltnerRSI (1d iš 1h) | +18,4 %, 26 % | +14,0 %, balanso 40,3 % | ⚠️ silpsta |
| abbasPublic | +20,0 %, 9,3 % | +13,2 %, balanso 34,7 % | ⚠️ silpsta −7 p. p. |
| eddies | +16,8 %, 9 % | +7,0 %, balanso 45 % | ❌ neišlaiko |
| NS4_dca | +17,1 %, 5,0 % | +12,6 %, balanso 23 % | ⚠️ silpsta −4,5 p. p. |
| NFI7HO2 | +15,0 %, 3,8 % | +9,7 %, balanso 27 % | ❌ neišlaiko |

Išvada: tvirčiausios EI3v2 (ir _2_4, _7), NASOS, E0V1E, ckNSJT, DS_Green_5m, BearBull3, BSS2b (su dideliu kritimu). abbas ir SMAO rezultatus išpūtė dabartinių monetų sąrašas.
