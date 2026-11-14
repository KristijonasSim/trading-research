# #48 Crypto Fear & Greed indeksas (alternative.me, nuo 2018-02) – ⚠️ trendo variantas rizikingų sąraše
Duomenys: `https://api.alternative.me/fng/?limit=0` (3204 dienos). Reikšmė su data D skelbiama D 00:00 UTC.
- **Kontrarinis** („pirk baimėje“): BTC 2021–26 −13…+10 %/m., ETH −24…−3 %/m. ❌ – populiarus patarimas neveikia.
- **Trendas: laikyti BTC/ETH, kai FGI > 60** (pozicija nuo kitos dienos): BTC+ETH 2018–21 +91 %/m., **2021–26 +24,5 %/m., kritimas 28 %**; BTC +19,9 % (25 %), ETH +27,5 % (34 %). 2022 m. 0 % (rinka −65 %).
- Jautrumas (`REZULTATAI_jautrumas.txt`): slenkstis 55–65 → +12…+25 %/m.; ≥ 70 → ~0. Vėlavimas 0 d. (švieži duomenys) 50–65 → +12…+21 %; 2–3 d. → +9…+13 %. Tipiškai ~+15 %/m.
- ⚠️ FGI daugiausia sudarytas iš kainos momentum ir volatilumo – tai trendo filtras; vienas signalas abiem monetoms; negalima patikrinti, ar istorinės reikšmės nebuvo perskaičiuotos.

- ✅ Nepriklausoma patikra ant alts10 (tas pats BTC rinkos signalas): FGI > 55/60/65 → 2021–26 +15,9 / +22,5 / +12,6 %/m. (laikymas −14 %), bet kritimai 45–57 % (`REZULTATAI_alts.txt`).

## Freqtrade (2026-11-14)
`freqtrade/user_data/strategies/papers/FearGreedTrend.py`: BTC+ETH 2021-11 – 2026-11 **CAGR +23,1 %, kritimas 13,9 %**, 112 sandorių (2022 – 0 sandorių), lookahead 0/20 (`results/validation/FearGreedTrend_lookahead.log`). Dry-run nuo 2026-11-14.
