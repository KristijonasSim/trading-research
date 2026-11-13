# Testų eilė (2026-11-13)
Svoriai bendram %: 1) svertas 10 %, 2) Kronos AI 15 %, 3) Bybit copy trading 15 %, 4) SSRN + Quantpedia 25 %, 5) 89 freqtrade strategijos 35 %.

| # | Darbas | Būsena | Padaryta |
|---|---|---|---|
| 1 | 3 botai su 2x/3x/5x svertu | baigta | 100 % |
| 2 | Kronos AI | praleista: saugumo filtras neleidžia, Kris gali paleisti pats | – |
| 3 | Copy trading lyderiai (Binance; Bybit nepasiekiamas demo režime) | baigta | 100 % |
| 4 | SSRN + Quantpedia | baigta | 100 % |
| 5 | 89 freqtrade strategijos (batchM14–M15, queue3.sh) | baigta | 100 % |

## Išvados (2026-11-13)
- **Svertas:** EI3v2 3x +107 %/m. (kritimas 29 %), NASOSv5_mod3 5x +87 %/m. (28 %) → `freqtrade/results/lev2/REZULTATAI.md`. Kitas žingsnis: 2018–21 su svertu, dry-run.
- **Copy trading:** Binance MoneyBoxTM (+90 %/365 d., kritimas 16 %, kopijuotojai +47k $) → `live-track-records/copy_trading.md`.
- **Quantpedia:** nieko geresnio už SPY → `quantpedia/REZULTATAI.md`.
- **89 freqtrade (batchM14–M15):** tinkamų nėra. IchiV1_Optimizable (+776 %/m.) atmesta – lookahead-analysis rado ateities duomenis. BreakoutDetector – tik 2 sandoriai.
