# Instagram: „day-trader-skill“ (Jakeschincariol, 11 Claude įgūdžių)

Įrašas (itstundeanthony): įdiegia įgūdžius, duoda 1000 $, rezultatas „TBD“. Repo: github.com/Jakeschincariol/day-trader-skill (`src/`, tik skaitytas, nepaleistas).

Kas viduje: ne AI prognozės, o paprasta taisyklė: 15 min. atidarymo rėžio prasimušimas (ORB), stop rėžio viduryje, tikslas 1:1, uždaryti iki 15:55. Kiti įgūdžiai yra pagalbiniai (naujienos, dydis, rizika, Alpaca pavedimai).

Testas (`test.py`, `REZULTATAI.txt`): 20 didžiausių JAV akcijų, 5 min., 2021–2026, 17 362 sandoriai.
- Laimi 50,3 %, vidutiniškai +0,017 R be kaštų, **−0,044 R su kaštais** (0,04 % per sandorį).
- Kiekvienais metais minuse. Tik 4 akcijos iš 20 (NVDA, TSLA, PLTR, AMD) nežymiai pliuse.
- Pats repo „Time Machine“ README pavyzdyje sako: „close to a coin flip“.
- Išvada: atmesta. Taip pat ORB anksčiau atmestas ant indeksų (`tradingview/scalp_test/`).
