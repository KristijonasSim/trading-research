# E0V1E_DCA3 su svertu (2026-11-10)
Binance futures, 10 altcoin'ų (XRP, BNB, SOL, DOGE, ADA, TRX, LINK, AVAX, LTC, DOT), 2021-11-08 – 2026-11-08,
mokestis 0,05 %, 1000 USDT, isolated. Strategija ta pati (`user_data/strategies/lev/E0V1E_DCA3_Lev.py`):
taisyklės mato pelną be sverto, kainos atstumai nepakitę. Paleisti: `bash results/lev/run.sh 1 3 5 10`.

| Svertas | %/m | Max kritimas | 1000 → | Blogiausias sandoris | 2025 m. |
|---|---|---|---|---|---|
| 1x | 16,2 | 6,5 % | 2120 | −24 % | +11 % |
| 2x | 18,3 | 55,7 % | ~2315 | −99 % (likvidacija) | −42 % |
| 3x | 41,7 | 51,6 % | 5714 | −99 % (likvidacija) | −30 % |
| 5x | 60,1 | 57,4 % | 10527 | −99 % (likvidacija) | −32 % |
| 10x | 53,4 | 70,7 % | 8516 | −99,9 % (2 likvidacijos) | −17 %, 2021 m. pirmas mėn. −32 % |

Priežastis: 2025-10-10 altcoin'ų kritimas (žvakės −50…−70 %). Su bet kokiu svertu ≥ 2x pozicijos likviduojamos.
Didelis %/m su 3–10x atsiranda tik dėl 2022–2024 m.; pikas 2025-09, po to −50…−70 %.
Be to, 1 min. detalumas anksčiau mažino rezultatą ~¼ – su svertu tai dauginama.
**Išvada: svertas pelną daugina, bet viena krizė nuneša pusę ar daugiau sąskaitos. 10x – pirmą mėnesį jau −32 %.**
