# Instagram: „absorbcija“ (zak.elga, volume + delta)

Teiginys: kaina krenta į didelės apyvartos zoną, agresyvūs pardavėjai spaudžia (raudona delta), bet naujos žemumos nėra → pirkėjai perima, kaina kils.
NQ tikrų pirkėjų/pardavėjų duomenų neturime, todėl testuota Binance futures BTC ir ETH 5 min. 2021–2026 (taker buy volume = tikra delta). `test.py`, skaičiai `REZULTATAI.txt`.

- **Absorbcija (long):** po signalo kaina 1 val. vidutiniškai pakyla +1…+9 bp. Bet ir be „absorbcijos“, tiesiog po stipraus pardavimo, kaina atšoka tiek pat ar daugiau (+5…+11 bp). Filtras nieko neprideda.
- **Absorbcija (short), atvirkštinė versija:** veikia ne į tą pusę.
- **Su 0,1 % kaštais visi variantai minuse** (−2…−22 bp/sandorį), abiem laikotarpiais.
- Išvada: atmesta. Įrašo autorius pats nurodo, kad grafikas tik iliustracija; komentatoriai rašo, kad delta dažnai prieštarauja kainai.
