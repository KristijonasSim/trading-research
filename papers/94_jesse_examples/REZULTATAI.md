# #94 Jesse pavyzdinės strategijos (KDJ, IFR2, SimpleBollinger) – ❌ atmesta (SimpleBollinger – išgyvenusiųjų iškraipymas)
BTC+ETH ir alts10, 4h ir 1d, 2018-06 – 2026-11; long-only 0,1 % ir long+short 0,05 %.
- KDJ ir IFR2: 2022–26 −23…+6 %/m. – atmesta.
- **SimpleBollinger 1d alts10** (long kai uždarymas > BB(20,2) viršutinė, išeiti < vidurinė):
  - pandas 2022–26 +17,0 %/m., kritimas 31 % (alts10 laikymas −7 %); 2018–21 +117 %/m.
  - **Freqtrade: 2021-11 – 2026-11 +15,3 %/m., balanso kritimas 35 %**, 312 sandorių, laimi 36 %, vid. +3,8 %; 5m detalumas – tas pats; 2018-06 – 2021-11 +138 %/m.; lookahead 0/20.
  - Jautrumas: BB(10–50, 1,5–2,5) 2022–26 dažniausiai +11…+18 %; be vienos monetos +14…+19 %; 0,2 % mokestis +15,5 %.
  - ⚠️ Metai: 2022 −27 %, 2025 −4 %, 2026 −10 % (pelnas 2023–24); BTC+ETH neveikia (+0,6 %). Kritimas 31–35 % – didesnis nei pagrindinio sąrašo.
- ❌ **Išgyvenusiųjų patikra (#95)**: su 2021-11 top 20 (įskaitant LUNA, FTT) 2021-11 – 2026-11 tik **+9,3 %/m., kritimas 34 %**; su 2018 top 10 2022–26 +6,9 %. Alts10 (dabartinės monetos) rezultatą išpučia ~8 p. p.
Failai: `test.py`, `robust.py` (ROBUST.txt), `freqtrade/user_data/strategies/papers/SimpleBollinger.py`.
