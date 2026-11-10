# QuantConnect forumas, 2 partija (2026-11-10)

Naujos temos: 3912, 8996, 17091, 19216, 11895, 9597 (In & Out originalas, 58 versijos), 2403, 15150, 4440, 3970, 11879, 15226, 12403, 18179, 17868, 2657, 14629.
Lean (Docker), 2021-11-08 – 2026-11-08, 0,1 % mokestis, dienos duomenys. Darbai: `quantconnect-lean/scripts/jobs_forum2.txt`, `jobs_forum3.txt`.
Palyginimui: laikyti SPY +10,9 %/m. (kritimas 24,5 %), laikyti QQQ +11,2 %/m. (35 %).

## Kas pavyko paleisti
- 74 versijos: 37 veikė, 22 nepadarė sandorių (parašytos minutiniams duomenims), 11 su klaidomis (reikia minutinių duomenų, XIV nebeegzistuoja, seni API).
- Runner'is papildytas naujo QuantConnect API (`set_start_date`, `initialize`) palaikymu.

## Geriausi „kaip paskelbta“ ir ką parodė patikra
| Versija | Kaip paskelbta | Ištaisyta | Kodėl |
|---|---|---|---|
| In & Out b99c4d7ebb | +12,4 %/m., kritimas 18 % | +0,5 %/m., 43 % (su obligacijomis) | SPY nupirktas pradžioje ir niekada neparduotas → visada ~2x svertas |
| In & Out 7aa1cbe215 | +11,0 %/m., 23 % | +1,6 %/m., 25 % | pradžioje ~2x svertas, auksas likdavo visam laikui |
| Leveraged ETFs (8996) b669b12c36 | +8,8 %/m., 45 % | – | blogiau už QQQ, didelis kritimas |
| QQQ/SPY rotation (19216) | +5,0 %/m., 32 % | – | blogiau už laikymą |
| Kiti (sektorių rotacija, RSI, VIX) | ≤ 0 %/m. | – | netinka |

## In & Out signalas atskirai (`tradingview/qqq3_trend/inout.py`, pandas, 2008–2026)
| | 2008–14 | 2015–20 | 2021–26 (po paskelbimo) |
|---|---|---|---|
| Laikyti QQQ | 11,6 % (49 %) | 21,4 % (29 %) | 11,2 % (35 %) |
| In & Out QQQ, išėjus obligacijos | 24,3 % (15 %) | 15,6 % (13 %) | 1,9 % (37 %) |
| In & Out QQQ, išėjus grynieji | 14,5 % (16 %) | 10,8 % (13 %) | 6,5 % (17 %) |
| In & Out 3x, išėjus grynieji | 43,0 % (43 %) | 30,6 % (36 %) | 6,3 % (50 %) |
Signalai sutampa su Lean beveik dieną į dieną. 2008–2020 – autoriaus kūrimo laikotarpis; po paskelbimo pranašumas išnyko (tik mažesnis kritimas).

## Išvada
Nė viena nauja QuantConnect forumo strategija po klaidų ištaisymo nelenkia QQQ/SPY laikymo. Geri rezultatai atsirado iš kodo klaidų (paslėpto sverto).
