# Volatility Breakout (vartotojo TradingView indikatorius), 2026-11-09

Kodas: `vb.py` (taisyklės 1:1 su Pine), duomenys: Dukascopy 15m 2017–2026 (`fetch.py`), rezultatai: `results/results.csv`, `results/summary.md`.

## Kaip testuota
- 5 instrumentai: NAS100, US30, SPX500, GER40, XAUUSD. Rėmai: 1D, 4h, 1h, 15m.
- Įėjimas/išėjimas kitos žvakės atidarymu. Tik long. Kaštai: 0,02 % į vieną pusę + 6 %/m. CFD finansavimas laikant poziciją.
- „Originalus“ = tie patys skaičiai (9/21/55, BB 20, ATR 14, Z 60, slenkstis 1,2, stop 1,5×ATR) bet kuriame rėme.
- „Pritaikytas“ = visi ilgiai × s, slenkstis ir stop parinkti 2017–2022 (mokymas), rezultatas 2023–2026 (nematytas).

## Rezultatai (2023–2026, %/m.)
| | Laikyti | 1D orig. | 1h orig. | 1h pritaik. top1 | 15m pritaik. top1 |
|---|---|---|---|---|---|
| NAS100 | 26,8 | −0,6 | 4,9 | 7,1 | 6,0 |
| US30 | 12,1 | −4,9 | −2,8 | −2,5 | −5,0 |
| SPX500 | 18,7 | −3,0 | −0,2 | 2,8 | 1,2 |
| GER40 | 17,0 | −2,6 | 0,9 | −1,1 | −0,2 |
| XAUUSD | 23,0 | 7,6 | 7,5 | 2,8 | 1,5 |

## Išvada
- Pine kodas, toks kaip pateiktas, dienos grafike „pirkti ir laikyti“ nelenkia: NAS100 2017–2026 28 sandoriai, vidutinis −0,3 %. Trailing stop 1,5×ATR išmeta per 1–3 savaites, rinkoje būna tik 10–20 % laiko.
- 1h/15m su originaliais skaičiais: per daug sandorių (50–200/m.), kaštai suvalgo.
- Geriausias pritaikymas: NAS100 1h, ilgiai ×2, slenkstis 2,0, stop 6×ATR → +7 %/m., kritimas 8 %, ~14 sandorių/m., rinkoje 24 % laiko. Mažiau nei laikymas (+27 %/m.), bet ir rizika daug mažesnė.
- Reikia patikrinti, kaip TradingView buvo matomas pranašumas (gal kita versija / strategy() su kitais nustatymais).
