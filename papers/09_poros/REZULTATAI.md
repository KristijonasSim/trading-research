# #9 Kripto porų prekyba (Fil, Kristoufek 2020) – ❌ atmesta

Kas savaitę (1h) ar kas dieną (5m) atrenkamos 5 geriausios poros: kointegracijos (Engle-Granger) arba atstumo metodu. Įeinama, kai |z| > 2, išeinama, kai z grįžta į 0, stop ties |z| > 4. Skriptai `test.py` (1h, 8 monetos nuo 2019) ir `test5m.py` (5m, 12 monetų, 2020–2026), lentelės `REZULTATAI.txt`, `REZULTATAI_5m.txt`.

| Variantas | Be mokesčio | 0,02 % | 0,1 % |
|---|---|---|---|
| 1h, atstumas, 30 d. | 2019–21 −17 %/m., 2022–26 −1 %/m. | −19 / −4 | −29 / −15 |
| 1h, kointegracija, 30 d. | −17 / −4 | −19 / −6 | −26 / −13 |
| 5m, atstumas, 10 d. | −6 %/m. | −21 | −61 |
| 5m, kointegracija, 3 d. | −10 %/m. | −43 | −91 |

- Nuostolinga **net be mokesčių**: kripto porų skirtumai linkę toliau tolti, o ne grįžti (ypač 2021 m.), be stop-loss dar blogiau.
- Straipsnio rezultatai (2018–19, 5 min.) nebeatsikartoja.
