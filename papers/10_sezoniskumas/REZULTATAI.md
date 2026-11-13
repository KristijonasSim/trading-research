# #10 Kripto valandų / savaitės dienų sezoniškumas (walk-forward) – ❌ atmesta

8 monetos (BTC, ETH, BNB, LTC, XRP, ADA, TRX, LINK), Binance 1h nuo 2017. Kiekvieniems metams 2020–2026 „geri“ langeliai (valanda UTC, savaitės diena arba diena×valanda) parenkami **tik iš ankstesnių metų** (vidurkis > 0, t-stat > 0/1/2). Mokestis 0,1 % už pirkimą ir pardavimą. Skriptai `test.py`, `nofee.py`, pilna lentelė `REZULTATAI.txt`.

| BTC 2020–26 | %/m. | kritimas | laiko rinkoje |
|---|---|---|---|
| Laikyti | +39,0 | 77 % | 100 % |
| Savaitės diena (t>0) | +23,2 | 73 % | 73 % |
| Valanda (t>1) | −97 | 100 % | 57 % |
| Diena×valanda (t>2) | −34 | 94 % | 6 % |

- Valandų efektas **egzistuoja**: pasirinktomis valandomis vidutiniškai +1–2 bp/val. daugiau nei vidurkis (be mokesčių BTC +35 %/m., BNB +74 %/m.).
- Bet kiekvienas įėjimas ir išėjimas kainuoja 20 bp – mokestis suvalgo viską, visos valandinės versijos bankrutuoja.
- Savaitės dienų versija mokesčius atlaiko, bet nė vienai monetai patikimai nelenkia laikymo (BTC +23 % vs +39 %, ETH +52 % vs +48 % su tokiu pat kritimu).
