# Trading research

Tikslas: rasti ir patikrinti **kitų žmonių jau sukurtas** strategijas (trumpalaikes ir ilgalaikes). Savų strategijų nekuriame.

## Įrankiai

| Folderis | Įrankis | Kam |
|---|---|---|
| `freqtrade/` | Freqtrade + freqtrade-strategies | Kripto. Dešimtys paruoštų strategijų, backtest, lookahead-analysis |
| `octobot/` | OctoBot | Kripto. Paruošti grid / DCA robotai, TradingView signalai |
| `quantconnect-lean/` | QuantConnect Lean | Akcijos per IBKR. Bendruomenės strategijos |
| `ib_async/` | ib_async | Python valdymas IBKR sąskaitai (vykdymui, ne strategijų paieškai) |
| `vectorbt/` | vectorbt | Greitas tūkstančių variantų testavimas |
| `backtesting-py/` | backtesting.py | Paprastas vienos strategijos testas |
| `results/` | — | Visų testų rezultatai ir palyginimai |

## Testavimo taisyklės

1. Visos strategijos testuojamos tais pačiais duomenimis ir mokesčiais.
2. Lyginama su „pirkti ir laikyti“ (BTC / SPY).
3. Atmetamos strategijos, kurios „žiūri į ateitį“ (Freqtrade `lookahead-analysis`).
4. Testuojama viename laikotarpyje (pvz. 2023–2024), tikrinama dar nematytame (2025–2026).
5. Kas išgyvena, tas leidžiamas demo / dry-run režimu 1–2 mėn. Tik po to mažomis realiomis sumomis.

## Šaltiniai

- strat.ninja: Freqtrade strategijų reitingai
- github.com/iterativv/NostalgiaForInfinity, github.com/freqtrade/freqtrade-strategies
- QuantConnect bendruomenės strategijos
