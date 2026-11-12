# Instagram: „efektyvi riba“ (silk.mechanics, Markowitz)

Teiginys: tinkamai sumaišius turtą, galima turėti mažiau rizikos už tą patį pelną.
Testas (`test.py`, `REZULTATAI.txt`): 12 ETF (SPY, QQQ, IWM, EFA, EEM, TLT, IEF, SHY, LQD, GLD, DBC, VNQ), kas mėnesį mišinys parenkamas pagal paskutinius 3 m., 2009-01–2026-11, 0,05 % kaštai.

| Portfelis | %/m. | svyravimai | kritimas |
|---|---|---|---|
| Maks. grąža/rizika (riba) | 3,2 | 5,3 | 14 |
| Min. rizika | 1,7 | 1,3 | 5,6 |
| Ribos taškas su 1/N rizika | 11,0 | 11,4 | 22 |
| Po lygiai (1/N) | 8,7 | 10,4 | 21 |
| 60/40 SPY/IEF | 10,2 | 10,1 | 21 |
| SPY | 15,3 | 17,6 | 34 |

- Pagal praeitį „geriausias“ portfelis žadėjo grąžos ir rizikos santykį 2,0, realiai gavo 0,6. Optimizatorius 72 % laikė trumpalaikėse obligacijose (SHY).
- „Min. rizika“ yra beveik vien pinigai: 1,7 %/m., mažiau už infliaciją.
- Ribos taškas su ta pačia rizika kaip 1/N davė +2,3 %/m. daugiau, bet 2021–26 m. buvo blogesnis už 1/N. Paprastas 60/40 duoda tą patį be skaičiavimų.
- Išvada: idėja teisinga (maišyti verta), bet optimizavimas pagal praeitį pranašumo neduoda. Saugesni ETF portfeliai: `etf-rotation/` (LAA, HAA, Permanent).
