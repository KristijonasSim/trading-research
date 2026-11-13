# #19 Larry Williams volatilumo pramušimas (Korėjos kripto botų versija) – ❌ atmesta

Pirkti, kai kaina > atidarymas + k × (vakar H − L), parduoti kitos dienos atidarymu. Binance spot dienos žvakės, mokestis 0,1 %. Skriptas `test.py`, lentelė `REZULTATAI.txt`.

| BTC+ETH | 2018–2021-11 %/m. (kritimas) | 2021-11–2026-11 %/m. (kritimas) |
|---|---|---|
| k=0,5 (klasika) | +96 (17 %) | −9,0 (53 %) |
| k=0,7 | +103 (15 %) | +5,3 (32 %) |
| triukšmo k + MA5 + 2 % dydis | +34 (7 %) | +2,4 (18 %) |

Alts10 visi variantai 2021–26 minuse (−2…−20 %/m.). Iki 2021 m. puikiai, bet vėliau nustojo veikti. Skirtumas nuo Dual Thrust (#18): riba skaičiuojama iš vienos dienos diapazono, todėl įeinama per dažnai.
