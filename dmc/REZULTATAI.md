# DMC indikatoriaus backtestas (NAS100 1 min. → 5/15 min., 2016–2026)

Logika ta pati kaip `tradingview/DMC_indikatorius.pine` (`dmc/test.py`, visi variantai `dmc/REZULTATAI.txt`). Kaštai ~2 t. sandoriui.

| Variantas | Sandorių/m. | Laimi | Vid. R | 1 % rizika |
|---|---|---|---|---|
| 5 min., 4H kryptis, 9:30–11:30 | 291 | 29 % | −0,13 | −34 %/m. |
| 15 min., 4H kryptis, 9:30–11:30 | 201 | 36 % | −0,10 | −19 %/m. |
| 15 min., tik BUY | 112 | 38 % | −0,10 | −12 %/m. |
| 5 min., be krypties filtro | 481 | 28 % | −0,15 | −56 %/m. |
| 15 min., sesija iki 16:00 | 339 | 38 % | −0,09 | −27 %/m. |

- **Visi variantai nuostolingi, beveik kiekvienais metais.** Net be kaštų −0,04 R/sandorį (5 min.).
- SL suveikia 56–71 % atvejų: „dagtis per lygį ir uždarymas atgal“ dažnai kartojasi ir kaina vis tiek eina toliau.
- Krypties filtras ir 15 min. šiek tiek mažina nuostolį, bet pliuso neduoda.
- Išvada: mechaninė DMC versija neveikia. Autoriaus „90 %“ remiasi jo paties sprendimais „iš akies“, kurių į taisykles perkelti nepavyksta. Indikatorių naudoti tik kaip lygių žemėlapį, ne signalams.
