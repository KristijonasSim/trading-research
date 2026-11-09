# Dvi geriausios strategijos (2026-11-09): perdavimas kitam agentui

Atsakyk vartotojui lietuviškai, trumpai, paprastais žodžiais (žr. `../CLAUDE.md`).

## Ką darėme
Ieškojome **kitų žmonių sukurtų** strategijų ir visas testavome tomis pačiomis taisyklėmis:
2021-11-08 – 2026-11-08, pradžia 1000, mokestis 0,1 % nuo sandorio, lyginame su „pirkti ir laikyti“.

| Šaltinis | Kiek testuota | Rezultatai |
|---|---|---|
| Freqtrade (kripto) | 65 strategijos | `../results/freqtrade_ranking.md`, `SUVESTINE.md` |
| OctoBot (kripto + indeksai/auksas) | 18 robotų + 3 grid × 4 rinkos | `../results/octobot_ranking.md` |
| QuantConnect biblioteka (akcijos/ETF, forex) | 25 iš 83 (kitoms reikia mokamų duomenų) | `../results/quantconnect_ranking.md` |
| QuantConnect forumas (5 populiarios temos) | 60 versijų | tas pats failas, skyrius „forumas“ |

Išvada: dauguma strategijų pralaimi paprastam „pirkti ir laikyti“. Liko dvi kandidatės.

## 1. CombinedBinHAndCluc (Freqtrade, kripto)
- Failas: `CombinedBinHAndCluc_freqtrade.py` (originalas `freqtrade/user_data/strategies/spot/`).
- Kas tai: 5 min. žvakės, perka staigius kritimus žemiau Bollinger juostos (dvi taisyklės: BinHV45 ir ClucMay72018), parduoda grįžus aukštyn. Day trading.
- Rezultatas (top 10 altcoin'ų): **+9,1 %/m.**, 1000 → 1546, max kritimas **14,6 %**. Altcoin'ų „laikyti“: 1000 → 620.
- `lookahead-analysis`: švari (nežiūri į ateitį).
- Silpna vieta: testuota tik viename laikotarpyje.

## 2. In & Out su TQQQ/TMF (QuantConnect forumas, akcijos/ETF)
- Failas: `in_and_out_tqqq_tmf_quantconnect.py` (forumo tema 9632, backtest `b34d9b7dda...`).
- Kas tai: kasdien tikrina „pavojaus signalus“ (pramonė XLI, metalai DBB, žaliavos IGE, obligacijos SHY, doleris UUP, auksas/sidabras, komunalinės/pramonė, CHF/AUD). Jei kuris nors labai nukrenta, pereina į obligacijas (TMF/TYD), kitaip laiko akcijas.
- Rezultatas (dieninės kainos, Lean lokaliai): **+13,1 %/m.**, 1000 → 1851, max kritimas **31 %**, 2022 m. **+35 %**. SPY „laikyti“: 1676, kritimas 25 %.
- **Įspėjimai:**
  - Kode yra svorių klaida: `self.wt` žodyne lieka ir `TQQQ: 1`, ir `SPY: 1`, todėl būnant „viduje“ realiai daugiausia laikomas SPY (pagal orderius: TQQQ nupirkta tik kartą, SPY 27 kartus). Rezultatas nėra „gryna TQQQ“ strategija. Reikia patikrinti orderių žurnalą ir ar nėra sverto per 100 %.
  - Išrinkta kaip geriausia iš 60 forumo versijų, todėl dalis rezultato gali būti sėkmė.
  - Originalas prekiauja minutinėmis kainomis 2 val. po atidarymo. Mes turėjome tik dienines (Yahoo), nes nemokamų valandinių šiems ETF nėra.

## Ką reikia padaryti toliau
1. **Patikrinti nematytame laikotarpyje** (2015-01-01 – 2021-11-07), abi strategijas, tomis pačiomis taisyklėmis.
   - Freqtrade: `freqtrade download-data` nuo 2015 (Binance altcoin'ams istorija trumpesnė, naudoti kas yra).
   - In & Out: Yahoo dienos kainos nuo 2014 (`quantconnect-lean/scripts/fetch_daily.py`, pakeisti datas), paleisti `scripts/run_lean.py` su kitu langu (datos įrašytos `patch()` funkcijoje ir `WRAPPER`).
2. **In & Out su valandinėmis IBKR kainomis.** Vartotojas turi IBKR. Reikia TWS/Gateway prisijungimo (paprašyti vartotojo), `ib_async` atsisiųsti 1h barus visiems 14 tickerių, konvertuoti `scripts/build_lean_data.py` formatu, paleisti su `hour`.
3. In & Out: ištaisyti/įvertinti svorių klaidą (TQQQ+SPY), paleisti abu variantus ir palyginti.
4. Kas išgyvena 1–3: dry-run / demo 1–2 mėn. (Freqtrade `dry_run`, IBKR paper account), tik tada maži realūs pinigai.

## Kaip paleisti
- QuantConnect: `cd quantconnect-lean && .venv/bin/python scripts/run_lean.py "<aplankas sources/strategies>" <variantas> daily|hour`.
  Reikia: `docker pull quantconnect/lean`, duomenų (`scripts/fetch_daily.py`, `fetch_hour.py`, `build_lean_data.py`). Forumo strategijos: `sources/forum/<tema>/<backtest>/`, simlinkai `sources/strategies/F<tema> ...`.
- OctoBot: `cd octobot && scripts/run_group.sh btc_eth`, ataskaita `scripts/report.py`.
- Freqtrade: žr. `../CLAUDE.md`.
