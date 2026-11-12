# Instagram: „8 trailing stop būdai“ (technicaltrading.tv, NQ)

Įrašas ne strategija: rodo 8 stop traukimo būdus vienam sandoriui ir teigia „joks stop nelaimi visada“.
Patikrinta NAS100 5 min., 2019–2026 (`test.py`, skaičiai `REZULTATAI.txt`), visi su pradiniu 2 ATR stop, uždaroma iki 15:55.

- **Atsitiktiniai įėjimai (5880):** nė vienas būdas nepaverčia atsitiktinių įėjimų pelningais. Swing low per 5 skirtingus atsitiktinius rinkinius vidutiniškai +0,3 bp, praktiškai nulis.
- **Prie Noise Breakout (1344 sandoriai):** originalus išėjimas +4,8 bp/sandorį, geriausias trailing (swing low) +1,8 bp, laikymas iki uždarymo +1,7 bp. Siauri stopai (paskutinės žvakės low, PSAR, 20 EMA) paverčia strategiją nuostolinga (−1,5…−2,0 bp).
- Išvada: Noise Breakout išėjimo nekeisti. Trailing stop pranašumo nesukuria, siauri stopai kenkia.
