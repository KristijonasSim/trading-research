# AI Forecast Cone (2026-11-10)

Failas: `tradingview/AI_Forecast_Cone.pine`. Išsaugota TradingView kaip „AI Forecast Cone“. Vaizdas: `ai/AI_Forecast_Cone_SPY.png`.

## Kas tai
Ne BUY/SELL signalai. Į ateitį piešiama violetinė vėduoklė: kur kaina bus per 10 žvakių su 50 % ir 80 % tikimybe, punktyrinė tikėtiniausio kelio linija, ribų kainos ir AI tikslumo kortelė. Taškai praeityje – senos AI prognozės (matosi, ar kaina tilpo).
AI: online kvantilių mokymasis (conformal prediction) – po kiekvienos žvakės ribos pačios prisitaiko; viršus ir apačia mokosi atskirai, todėl vėduoklė pasvyra ten, kur rinka realiai juda.

## Ką išbandžiau prieš tai (19 rinkų, 2008–2026, `ai/*.py`)
| AI būdas | Rezultatas |
|---|---|
| Online logistinė regresija: ar kils per 5–20 d. | Pranašumo nėra (−0,1…−3 p.p.) |
| AI kritimo rizikos modelis | Neveikia (AUC < 0,5) |
| kNN panašios situacijos (Lorentz atstumas) | Krypties pranašumo nėra |
| AI renkasi iš 7 žinomų signalų (Hedge) | Blogiau už vieną gerą signalą |
| **Save kalibruojančios kainos ribos** | **Veikia** |

## Patikra
- Python, 19 rinkų: 80 % zona pataikė 80 % abiem laikotarpiais, kiekvienoje rinkoje 78–83 %. Paprasta ATR juosta: 91–93 % (be reikalo per plati).
- TradingView SPY dienos: 80 % zona pataikė 81 %, 50 % zona – 50 %.

## Kam naudoti
Stop vieta (apatinė 80 % riba = 10 % šansas ją pasiekti), realūs tikslai, opcionų ribos, įspėjimai, kai kaina išeina už AI zonos (neįprastas judesys). Kur kils kaina, nespėja – to joks AI būdas nepadarė patikimai.
