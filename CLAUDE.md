# Trading research: kontekstas naujam botui

Atsakyk lietuviškai, trumpai, be barbarizmų. Detales rašyk į failus, ne į pokalbį.

## Tikslas
Rasti ir patikrinti **kitų žmonių jau sukurtas** prekybos strategijas (kripto ir akcijos, trumpalaikes ir ilgalaikes). **Savų strategijų nekuriame.**

## Testavimo taisyklės
1. Visos strategijos testuojamos tais pačiais duomenimis ir mokesčiais.
2. Lyginama su „pirkti ir laikyti“ (BTC/ETH, altcoin'ų krepšelis, akcijoms SPY).
3. Atmetama, jei strategija naudoja ateities duomenis (Freqtrade `lookahead-analysis`, `recursive-analysis`).
4. Testuojama viename laikotarpyje, tikrinama dar nematytame.
5. Kas išgyvena: dry-run / demo 1–2 mėn., tik tada mažos realios sumos.

## Svarbiausi failai
| Failas | Kas jame |
|---|---|
| `README.md` | Įrankių sąrašas ir šaltiniai |
| `results/SUVESTINE.md` | **Pradėk nuo čia.** Pagrindinės išvados, atrinktos strategijos, laukiantys sprendimai |
| `results/PROGRESS.md` | Darbų eiga su datomis (skriptai į jį rašo automatiškai) |
| `results/freqtrade_ranking.md` | Visų 65 strategijų lentelės pagal grupes ir metus |
| `results/freqtrade_all_results.csv` | Tie patys rezultatai CSV formatu |
| `results/validation/*.log` | Lookahead / recursive patikrų logai |

## Freqtrade (`freqtrade/`)
- Freqtrade 2026.10, Python 3.12, virtuali aplinka `freqtrade/.venv`.
- Konfigai: `config_spot.json` (mokestis 0,1 %), `config_futures.json` (0,05 %). Birža Binance, pradinis balansas 1000 USDT.
- Strategijos: `user_data/strategies/spot`, `.../futures`, `.../extra` (nepaleistos, žr. žemiau).
- Duomenys: `user_data/data` (jau atsiųsti, 2021-11-08 – 2026-11-08).
- Grupės: BTC+ETH ir top 10 altcoin'ų (XRP, BNB, SOL, DOGE, ADA, TRX, LINK, AVAX, LTC, DOT).

GitHub repo (github.com/KristijonasSim/trading-research) **neturi** šių failų, nes jie per dideli: `.venv/`, `user_data/data/`, `results/raw/`, `sources/` (klonuoti strategijų repo). Jei dirbi su nauja kopija, atkurk juos: `python3 -m venv .venv && .venv/bin/pip install freqtrade`, tada `freqtrade download-data` (Binance, 2021-11-08 – 2026-11-08, laikotarpiai 1m/5m/1h/4h).

Komandos (paleisti iš `freqtrade/`):
- `.venv/bin/python run_all.py -j 1`: visi backtestai. Baigtus praleidžia, todėl galima tęsti po perkrovimo (`-s <Strategija>` paleidžia vieną).
- `.venv/bin/python report.py`: sugeneruoja `results/freqtrade_ranking.md` ir CSV.
- `bash validate.sh`: lookahead/recursive patikros, logai rašomi į `results/validation/`.

## Būsena (2026-11-09)
- ✅ Atlikti 65 strategijų backtestai (oficialus `freqtrade-strategies` repo + NostalgiaForInfinityX8), 5 metai.
- ✅ Patikrintos 7 geriausios. Švarios: CombinedBinHAndCluc, ReinforcedAverageStrategy, Low_BB, VolatilitySystem (futures), UniversalMACD, BinHV45.
- ❌ NostalgiaForInfinityX8 atmesta, nes naudoja ateities duomenis (2 patikros: 4/18 ir 6/20 exit signalų).
- ⚠️ VolatilitySystem: +69,8 %/m., bet 2x svertas, be stop-loss, max kritimas 53 %.
- Geriausios saugesnės (altcoin'ai): CombinedBinHAndCluc +9,1 %/m., ReinforcedAverage +6,5 %/m., Low_BB +6,3 %/m. Altcoin'ų „pirkti ir laikyti“ per 5 m. iš 1000 USDT liktų 620.

## Laukia vartotojo sprendimo
1. **469 papildomos strategijos** `freqtrade/user_data/strategies/extra/` (HUGE_FreqTrade_Strategy_Collection, TheoBrigitte, i1ya, trendrider). **Nepaleistos:** kodas iš nežinomų autorių. `Ichi.py` kviečia `rm`, `Uptrend.py` naudoja `eval()`. **Nepaleisk be vartotojo leidimo.** Jei leis, saugiausia paleisti Docker konteineryje be interneto.
2. **Dry-run** 2–3 švarioms strategijoms (siūloma: CombinedBinHAndCluc, Low_BB, ReinforcedAverage ant altcoin'ų).
3. **VolatilitySystem** išbandyti saugesnę versiją (be sverto, su stop-loss).

## Dar nepradėta
Aplankai `octobot/`, `quantconnect-lean/`, `ib_async/`, `vectorbt/`, `backtesting-py/` tušti. Kitas logiškas žingsnis: QuantConnect Lean akcijoms per IBKR.

## Darbo tvarka
- Kiekvieną atliktą darbą įrašyk į `results/PROGRESS.md` su data.
- Svarbias išvadas atnaujink `results/SUVESTINE.md`.
- Šį failą atnaujink, kai pasikeičia būsena ar atsiranda naujų sprendimų.
