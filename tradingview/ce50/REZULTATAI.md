# Instagram: „CE 50% Model“ (cemarketsolutions, NQ)

Taisyklės (iš įrašo): 8:30–9:30 ET rėžis, padalintas per pusę. Pirmoji 3 min. žvakė nuo 9:30 užsidaro žemiau vidurio → short kitos žvakės atidarymu (aukščiau → long). Stop už rėžio krašto, traukiamas prie kiekvieno patvirtinto 15 min. swing high/low. Uždaryti 16:00. Autorius žada 59,37 %/m. (2016–2026, ¼ Kelly).

Testas: NAS100 1 min. (Dukascopy) 2016-01–2026-11, 2682 sandoriai, 0,01 % kaštai (`test.py`, `REZULTATAI.txt`).

- **Veikia, bet mažiau nei žadama.** Laimi 34 %, vid. +0,115 R/sandorį, 10 metų iš 11 pliuse (tik 2022 −0,01 R).
- 1 % rizikos sandoriui: 2016–21 +35 %/m. (kritimas 37 %), **nematytas 2022–26 +17 %/m. (kritimas 25 %)**. ¼ Kelly ≈ 1 % rizikos, tas pats.
- **Signalas tikras:** ta pati schema su atsitiktine kryptimi (4 bandymai) vid. ~0 R; visada long +0,03 R, visada short −0,02 R.
- Long pusė geresnė (+0,149 R, +18,6 %/m., kritimas 24 %) nei short (+0,077 R, +6,8 %/m., kritimas 48 %).
- Su dvigubais kaštais (0,02 %) lieka +0,071 R.
- Trūkumai: dideli kritimai (25–37 % prie 1 % rizikos); Noise Breakout turi daug geresnį grąžos ir kritimo santykį (~15 %/m., kritimas ~6 %). 59 %/m. neatsikartoja.
- Kitas žingsnis: patikrinti TradingView (tikri NQ futures duomenys), tada demo kartu su Noise Breakout.

## Tik long, visa sąskaita į 3x Nasdaq ETP (`qqq3.py`, `REZ_QQQ3.txt`)
- Uždarant 16:00 (TQQQ JAV biržoje): 2016–26 **+7,2 %/m.**, kritimas 35 %; 2022–26 +12,9 %/m. Metai labai nelygūs (2018 −18 %, 2022 −25 %, 2023 +52 %).
- QQQ3 LSE/Xetra uždaromas 11:30 ET, todėl sandorį tenka nutraukti anksčiau: **−0,9 %/m.**, neverta.
- Kodėl blogiau nei 1 % rizikos variantas (+18,6 %/m.): fiksuotas 3x neduoda didesnės pozicijos dienomis, kai stop arti; būtent tos dienos uždirba. Paprastas QQQ laikymas ~18 %/m.

## Tik long, NAS100 CFD su 3x svertu (iki 16:00, spread 0,01 %)
- 1x: +6,1 %/m., kritimas 11 %. **3x: +17,5 %/m., kritimas 29 %**; 2022–26 +23,4 %/m. (kritimas 27 %).
- Minuso metai: 2018 −9 %, 2020 −11 %, 2022 −19 %. Geriausi: 2023 +68 %, 2019 +47 %.
- Geriau nei TQQQ, nes CFD spread mažesnis (0,03 % prie 3x vs 0,1 %).

## 5 min. žvakė vietoj 3 min. (`test5m.py`)
- Prasčiau: vid. +0,077 R (vs +0,115), tik long +12,8 %/m. (vs +18,6), 2022–26 abiem kryptimis tik +1,4 %/m. Naudoti 3 min. žvakę.

## Maven Omo 2-Step $10k ($38), 2025-01 – 2026-11 (`maven.py`, `REZ_MAVEN.txt`)
Taisyklės: P1 +6 %, P2 +8 %, fiksuotas 8 % max nuostolis, 4 % per dieną, ≥3 pelningos dienos (≥0,5 %) kiekvienoje fazėje ir cikle, išmokėjimas kas 10 d. d., 80 %. **Maven puslapis rodo „not available in your region“.**
- Tik long, 1 % rizika: 4 sąskaitos, 2 kartus funded, išmokėta 125 $, išleista 152 $ → **−27 $**. 2 % rizika: +354 $.
- Long + short: 1 % rizika +1308 $ (5 sąskaitos, 3 funded), 2 % rizika +4513 $ (22 sąskaitos, 5 funded, išleista 836 $).
- Short pusė 2025–26 padėjo (balandžio 2025 kritimas). Rezultatai labai priklauso nuo kelių didelių dienų, mažai sandorių (224/457).
- Neįskaičiuota: Red Folder naujienų draudimas (±2 min.), galimas min. išmokėjimas.
- Didesnė rizika: 3 % long+short – 7 funded per 22 mėn. (0,31/mėn., 32 sąskaitos, +7158 $); 4 % – nė vieno (vienas pilnas stop + kaštai viršija 4 % dienos limitą). 1 funded per mėnesį su CE50 nepasiekiama.

## Visos atrinktos strategijos per Maven (`maven_multi.py`, `REZ_MAVEN_MULTI.txt`), 2025-01 – 2026-11 (22 mėn.)
Daugiausia funded per mėnesį (k = svertas, CE50 – rizika %):
- EI3v2 (kripto) k=6–10: 0,36–0,40/mėn. (8–9 funded, 22–26 sąskaitos, +2,8–4,6 tūkst. $).
- CE50 long+short 3 % rizika: 0,31/mėn. (7 funded, 32 sąskaitos, +7,2 tūkst. $).
- ckNSJT_morning k=5–10: 0,18/mėn., +6,6–16 tūkst. $ (4 funded, 7–10 sąskaitų).
- Noise Breakout: 0,09/mėn. (per mažai pelningų dienų ≥0,5 %); Noise+CE50 kartu: 0,18–0,22/mėn.
- E0V1E_DCA3, NASOSv5_mod3: 1 funded per visą laiką (lėti), bet funded sąskaita išgyvena ir moka.
**1 funded per mėnesį nepasiekia nė viena.** Kripto skaičiai per geri: skaičiuojamas tik uždarytų sandorių pelnas, atviri nuostoliai (pvz. 2025-10-10 kritimas) nematomi, o Maven kripto svertas gali būti mažas. Patikimiausias: CE50 (NAS100).
