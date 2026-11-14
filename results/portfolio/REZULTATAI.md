# Atrinktų freqtrade strategijų portfelis ir koreliacija (2022–2025)
Iš backtestų sandorių eksportų (`freqtrade/results/validate50/detail_*_none_*`), dienos grąža = uždarytų sandorių pelnas. ⚠️ Tik realizuotas pelnas – kritimai **neįvertina atvirų pozicijų** (tikri kritimai žr. ATRINKTI_BOTAI.md).
- 9 strategijos lygiais svoriais: **+23,2 %/m.** (2022–25), realizuoto kapitalo kritimas 3,3 %.
- **NASOSv5_mod3, NASMAO ir abbas – beveik ta pati strategija** (savaitinių grąžų koreliacija 0,84–0,88): portfelyje laikyti tik vieną (NASOS – mažiausias kritimas).
- E0V1E_DCA3 koreliuoja su NASOS 0,54; kitos poros −0,3…+0,36 – gera diversifikacija (EI3v2, ckNSJT, SMAO, MACDV, EMA800 tarpusavyje beveik nekoreliuoja).
- BTC+ETH strategijos (MACDV, EMA800) beveik nekoreliuoja su alts10 (≈ 0–0,25).
Skriptas `corr.py`, pilna lentelė `REZULTATAI.txt`. Išgyvenusiųjų patikra (2021-11 top 20) – `freqtrade/results/pit/pit.log`.
