# Swing Trend Pullback (2026-11-10, 30 min. užduotis)

Failas: `tradingview/Swing_Trend_Pullback.pine` (dienos grafikas). **Patikrinta TradingView**: kompiliuojasi be klaidų, rodo BUY (atšokimas / lūžis), ✓/✗ su %, stop liniją, lentelę.
TradingView SPY dienos, visa istorija: 81 sandoris, laimi 59 %, iš viso +1704 % vs laikant +1523 % (rezultatas pagal uždarymo kainą, apytikslis).

Taisyklės (iš žinomų sistemų): tik kai EMA50 > EMA200; pirkti, kai RSI(2) < 25 (Connors) arba lūžis virš 20 d. maksimumo (Turtle); išeiti, kai uždarymas < Chandelier stop (5 x ATR22, LeBeau). Trendo apsisukimas išėjimo nesukelia (galima įjungti).

Patikra Python: 19 rinkų (SPY, QQQ, IWM, DIA, GLD, TLT, EEM, EFA, XLE, XLK, XLF, AAPL, MSFT, AMZN, NVDA, JPM, XOM, BTC, ETH), Yahoo dienos, 0,1 % mokestis, pirkimas kitos dienos atidaryme. Skriptai `t2.py` (6 sistemos × 3 stop), `t3.py` (patobulinimai).

| Versija | 2005–14 %/m. / kritimas | 2015–26 %/m. / kritimas |
|---|---|---|
| Galutinė (RSI<25, 5 ATR, be trendo išėjimo) | 8,1 / −35 % | 10,4 / −32 % |
| Pirma (RSI<10, 4 ATR, su trendo išėjimu) | 6,4 / −29 % | 6,8 / −37 % |
| Pirkti ir laikyti | 8,0 / −58 % | 13,4 / −41 % |

Išvada: 2005–14 tokia pat grąža kaip laikant, bet kritimas beveik perpus mažesnis; 2015–26 grąža šiek tiek mažesnė, kritimas ~¼ mažesnis. Rinkoje ~60–65 % laiko.

## Palyginimas su populiariais indikatoriais (tos pačios 19 rinkų, `t4.py`, `t4_palyginimas.csv`)

| Vieta | Indikatorius | 2005–14 %/m. / kritimas | 2015–26 %/m. / kritimas |
|---|---|---|---|
| **1** | **Swing Trend Pullback (mano)** | **8,1 / −35 %** | **10,3 / −31 %** |
| 2 | Golden cross 50/200 | 5,9 / −32 % | 7,9 / −38 % |
| 3 | Supertrend 10/3 | 5,0 / −30 % | 5,7 / −35 % |
| 4 | EMA 9/21 | 3,7 / −35 % | 6,9 / −34 % |
| 5 | Turtle 20/10 | 3,5 / −28 % | 5,3 / −33 % |
| 6 | Supertrend + EMA200 | 3,3 / −25 % | 2,7 / −36 % |
| 7 | MACD 12/26/9 | 1,4 / −46 % | 4,5 / −34 % |
| 8 | Parabolic SAR | 0,5 / −45 % | 4,5 / −39 % |
| – | Pirkti ir laikyti | 8,0 / −58 % | 13,3 / −41 % |

Pagal grąžą ir grąžos/kritimo santykį pirma vieta abiem laikotarpiais. TradingView išsaugota kaip „Swing Trend Pullback“.
