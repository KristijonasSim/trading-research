# QuantConnect strategijų rezultatai

Variklis: QuantConnect Lean (Docker, lokaliai). Laikotarpis 2021-11-08 – 2026-11-08, mokestis 0,1 % nuo sandorio, rezultatai perskaičiuoti į 1000 pradžią. Dienos kainos: Yahoo (su dividendais), valandinės: Dukascopy.

**Pirkti ir laikyti SPY (S&P 500):** 10.9%/m., iš 1000 liktų 1676 (max kritimas 24.5%) — 2021: 1.6% | 2022: -18.2% | 2023: 26.2% | 2024: 24.9% | 2025: 17.7% | 2026: 8.7%

Forex strategijas lyginti su 0 % (grynieji), nes valiutų „pirkti ir laikyti“ neturi prasmės.

## akcijos/ETF

| name                                                | variant   | resolution   |   cagr_pct |   2021 |   2022 |   2023 |   2024 |   2025 |   2026 |   final_usdt |   max_drawdown_pct |   trades |
|:----------------------------------------------------|:----------|:-------------|-----------:|-------:|-------:|-------:|-------:|-------:|-------:|-------------:|-------------------:|---------:|
| CAPM Alpha Ranking Strategy on Dow 30 Companies     | 269807fc  | hour         |       14.3 |   17.6 |  -15   |   81.3 |   22.9 |   88.4 |  -53.5 |       1953.5 |               58.6 |      166 |
| January Barometer                                   | 46144084  | daily        |       14.1 |    0   |   -4.1 |   26.3 |   25.2 |   18.1 |    7.8 |       1931.3 |               18.7 |        6 |
| CAPM Alpha Ranking Strategy on Dow 30 Companies     | 269807fc  | daily        |       10.2 |    6.8 |  -20.1 |   65.8 |  -30.5 |   58.5 |    4.2 |       1623.7 |               63.1 |      179 |
| Asset Class Momentum                                | 661605c1  | daily        |       10.1 |    7.2 |   -5.5 |    3.5 |   14.8 |   24.6 |    7.7 |       1616.8 |               32.2 |       64 |
| Momentum Effect in Country Equity Indexes           | fb12003d  | daily        |        5.5 |   -2.1 |   -6.8 |   10.6 |    2.5 |   23.2 |    2.5 |       1306   |               16.2 |       21 |
| Sector Momentum                                     | a20b3eef  | daily        |        5.1 |    3.6 |   -9.3 |   18.5 |   -4.2 |    6.9 |   12.6 |       1283   |               24.5 |      238 |
| Paired Switching                                    | 672254ea  | daily        |        5   |    5.9 |  -21.4 |   20.6 |   25.2 |    5.8 |   -4   |       1276.7 |               22.8 |       21 |
| Momentum Effect in Country Equity Indexes           | 65aa7511  | daily        |        4.6 |    3   |  -32.1 |   28.5 |   19.4 |   36.9 |  -14.8 |       1252.6 |               37.5 |      213 |
| Asset Class Trend Following                         | b7f463f6  | daily        |        2.5 |   -1.3 |  -14.1 |    9.2 |    2   |    5.2 |   13.7 |       1129.7 |               30.9 |     1530 |
| CAPM Alpha Ranking Strategy on Dow 30 Companies     | 63ecf025  | hour         |        1   |    5.6 |  -36.4 |  -11.4 |   11.2 |   30.9 |   21.4 |       1051.5 |               51.7 |      170 |
| Pre-Holiday Effect                                  | 3efe3012  | hour         |        0.9 |   -1.1 |    3.7 |    0.3 |    4.8 |   -3.5 |    0.4 |       1044.9 |                5.8 |       68 |
| Optimal Pairs Trading                               | e9e74232  | hour         |        0   |    0   |    0   |    0   |    0   |    0   |    0   |       1000   |                0   |        0 |
| Optimal Pairs Trading                               | e9e74232  | daily        |       -0.1 |    0   |  -10   |    6.7 |    5.6 |   -0.3 |   -1.6 |        994.8 |               21   |       28 |
| Momentum and Style Rotation Effect                  | 3a10f60f  | daily        |       -0.3 |   -1.9 |   -7.1 |    3.6 |    0.5 |   -4.1 |    8.2 |        985.3 |               12.7 |      155 |
| Turn of the Month in Equity Indexes                 | 9135d988  | daily        |       -0.5 |   -0.1 |   -1.7 |   -0.5 |   -0.5 |   -5.8 |    6.5 |        974.6 |               13.8 |      120 |
| Pairs Trading with Stocks                           | 696b4b24  | daily        |       -0.6 |   -3   |    2.2 |   -6.1 |    1.5 |   -0.9 |    3.5 |        968.5 |               16.4 |      434 |
| Pre-Holiday Effect                                  | 3efe3012  | daily        |       -0.7 |    1.1 |    1.8 |    1.6 |   -1.7 |   -4.6 |   -1.4 |        967.6 |                7.8 |       68 |
| Mean Reversion Effect in Country Equity Indexes     | ef28d712  | daily        |       -1.4 |   -2.5 |   12.1 |   -1.9 |   -9.2 |   -6.9 |    2.8 |        931.2 |               20.4 |       16 |
| Beta Factor in Country Equity Indexes               | d83ddc77  | daily        |       -2   |    0.3 |   -3.2 |   -4.9 |   -4.3 |    1.6 |    0.7 |        903.8 |               18.9 |      548 |
| Pairs Trading with Country ETFs                     | 6d54f129  | daily        |       -2.5 |   -1   |   -2.2 |    1.1 |  -10.7 |  -15   |   18.5 |        880   |               37.9 |     1796 |
| Turn of the Month in Equity Indexes                 | 9135d988  | hour         |       -2.6 |   -1.4 |   -1.4 |   -1.6 |   -4.3 |   -2.7 |   -1.4 |        878   |               12.2 |      120 |
| CAPM Alpha Ranking Strategy on Dow 30 Companies     | 63ecf025  | daily        |       -3.2 |   21.3 |  -57.6 |   -8.9 |   -5.4 |   40.4 |   36.3 |        847.8 |               70.4 |      192 |
| Dual Thrust Trading Algorithm                       | b3c3d8da  | hour         |       -4.1 |  -13   |   20.9 |    5.7 |   -5.3 |  -17.5 |   -6.7 |        810.2 |               34   |      788 |
| Dual Thrust Trading Algorithm                       | b3c3d8da  | daily        |       -8   |   -5.4 |   11.7 |   -1   |   -7.5 |  -26.9 |   -7   |        657.4 |               49   |      413 |
| Overnight Anomaly                                   | 0c606c13  | hour         |      -14.9 |    0.6 |  -35.3 |   -0.7 |  -15.7 |   -7.5 |  -11.2 |        447.5 |               55.8 |     1255 |
| Overnight Anomaly                                   | 0c606c13  | daily        |      -15.2 |   -0.6 |  -34   |   -1.9 |  -12.3 |  -14.8 |   -9   |        437.3 |               57.6 |     1255 |
| Forecasting Stock Prices using a Temporal CNN Model | e8157014  | daily        |      -41.3 |   -3.1 |  -48.7 |  -39.1 |  -28   |  -48.9 |  -37.3 |         69.8 |               93.3 |     4944 |

## forumas

| name                                                     | variant    | resolution   |   cagr_pct |   2021 |   2022 |   2023 |   2024 |   2025 |   2026 |   final_usdt |   max_drawdown_pct |   trades |
|:---------------------------------------------------------|:-----------|:-------------|-----------:|-------:|-------:|-------:|-------:|-------:|-------:|-------------:|-------------------:|---------:|
| forum Amazing returns  superior stock selection strateg  | cca9a02d5b | daily        |       14.3 |    4.7 |  -31.2 |   47.9 |   18.2 |   41.9 |    9.2 |       1949.4 |               47.8 |      155 |
| forum Amazing returns  superior stock selection strateg  | b34d9b7dda | daily        |       13.1 |   -0.8 |   35.3 |   15   |   13.2 |    5.1 |    0.8 |       1851.4 |               31   |       71 |
| forum Amazing returns  superior stock selection strateg  | daaa3c540b | daily        |        7   |    0.5 |  -38.6 |   58   |    2.5 |   29.2 |    8.4 |       1400.2 |               41.9 |      466 |
| forum Dual Momentum with Out Days - QuantConnect.com     | 47f1fd3355 | daily        |        3.4 |    0.9 |   75   |  -31.5 |    5   |   -9.9 |    3.6 |       1184   |               41.1 |     1684 |
| forum 3X ETF Short Hedge Algorithm - QuantConnect.com    | caa0495f22 | daily        |        1.2 |    1.7 |    0.5 |    4.9 |   -5.4 |    2.3 |    2.3 |       1061   |               16   |     5626 |
| forum Using Levered ETFs in IRA - 10 years - 24% CAGR, 1 | f0d8f50c73 | daily        |        0.2 |    2.6 |  -32.2 |   19.6 |   25.2 |   11.3 |  -12.9 |       1009   |               38.8 |       63 |
| forum Dual Momentum with Out Days - QuantConnect.com     | 3aa1830197 | daily        |        0   |    0   |  nan   |  nan   |  nan   |  nan   |  nan   |       1000   |                0   |        0 |
| forum Amazing returns  superior stock selection strateg  | 8e5ac08df2 | daily        |        0   |    0   |    0   |    0   |    0   |    0   |    0   |       1000   |                0   |        0 |
| forum Amazing returns  superior stock selection strateg  | 4d3c02f3fc | daily        |        0   |    0   |    0   |    0   |    0   |    0   |    0   |       1000   |                0   |        0 |
| forum Amazing returns  superior stock selection strateg  | 665fbb24e9 | daily        |        0   |    0   |    0   |    0   |    0   |    0   |    0   |       1000   |                0   |        0 |
| forum Amazing returns  superior stock selection strateg  | 73c23e66bd | daily        |        0   |    0   |    0   |    0   |    0   |    0   |    0   |       1000   |                0   |        0 |
| forum Amazing returns  superior stock selection strateg  | 1bb502e471 | daily        |        0   |    0   |    0   |    0   |    0   |    0   |    0   |       1000   |                0   |        0 |
| forum Amazing returns  superior stock selection strateg  | 1c1cbe327d | daily        |       -0   |    0.5 |  -34.8 |   33.3 |   11.8 |    8.6 |   -5.9 |        998.2 |               37.9 |      462 |
| forum Amazing returns  superior stock selection strateg  | 6c7e6f68cf | daily        |        0   |    0   |    0   |    0   |    0   |    0   |    0   |       1000   |                0   |        0 |
| forum Amazing returns  superior stock selection strateg  | d7eb6b2089 | daily        |        0   |    0   |    0   |    0   |    0   |    0   |    0   |       1000   |                0   |        0 |
| forum Amazing returns  superior stock selection strateg  | 668f08eb95 | daily        |        0   |    0   |    0   |    0   |    0   |    0   |    0   |       1000   |                0   |        0 |
| forum Amazing returns  superior stock selection strateg  | 9edefa25d1 | daily        |        0   |    0   |    0   |    0   |    0   |    0   |    0   |       1000   |                0   |        0 |
| forum Amazing returns  superior stock selection strateg  | 68267ac216 | daily        |        0   |    0   |    0   |    0   |    0   |    0   |    0   |       1000   |                0   |        0 |
| forum Amazing returns  superior stock selection strateg  | c316bceaaa | daily        |       -0.1 |   -0.3 |  -22.8 |   13   |   10.3 |    4   |   -0.5 |        993.7 |               26.5 |       61 |
| forum Dual Momentum with Out Days - QuantConnect.com     | c66e80139b | daily        |       -0.9 |   -1   |   77.3 |  -33   |   -7.9 |  -16.2 |    5.4 |        957.2 |               54.4 |      417 |
| forum 3X ETF Short Hedge Algorithm - QuantConnect.com    | b7958208f0 | daily        |       -1.3 |    0   |   -5   |    1.8 |  -13   |  -12   |   26.7 |        937.1 |               34.6 |      113 |
| forum 3X ETF Short Hedge Algorithm - QuantConnect.com    | 25166e99bf | daily        |       -1.3 |    0   |   -5   |    1.8 |  -13   |  -12   |   26.7 |        937.1 |               34.6 |      113 |
| forum Dual Momentum with Out Days - QuantConnect.com     | 636462c941 | daily        |       -1.6 |    3.1 |   42.6 |  -23.9 |    4.4 |  -16.3 |   -5.9 |        920.6 |               53.9 |    22321 |
| forum Dual Momentum with Out Days - QuantConnect.com     | 758574589e | daily        |       -1.6 |   -0.6 |   46   |  -14.8 |  -16.7 |  -15   |    5.4 |        923.2 |               49.1 |      107 |
| forum Amazing returns  superior stock selection strateg  | cc18cfc59f | daily        |       -2.2 |   -0.3 |  -23.5 |    8.8 |   14.5 |   -1   |   -4.9 |        894.7 |               28.9 |       86 |
| forum Amazing returns  superior stock selection strateg  | eb5bf1f328 | daily        |       -2.2 |   -0.3 |  -52.8 |   60   |   19.6 |   13.5 |  -12.5 |        893.3 |               56.7 |       85 |
| forum Dual Momentum with Out Days - QuantConnect.com     | 8689604307 | daily        |       -2.9 |   -4.2 |   29.2 |  -32.1 |    7   |   -8.1 |    4.2 |        861.6 |               40.2 |      502 |
| forum Dual Momentum with Out Days - QuantConnect.com     | 0d613d724b | daily        |       -3.4 |    1.5 |   17.6 |  -26.9 |    4.1 |  -10.5 |    3.4 |        839.3 |               49.7 |     4611 |
| forum Using Levered ETFs in IRA - 10 years - 24% CAGR, 1 | c0caa05e49 | daily        |       -4   |    0.4 |  -55.6 |   44.3 |    8.1 |   17.9 |   -0.5 |        816.6 |               58.1 |      165 |
| forum Using Levered ETFs in IRA - 10 years - 24% CAGR, 1 | 316dcfe1c5 | daily        |       -4   |   -1.7 |  -55.9 |   45   |    9.6 |   21.3 |   -2.4 |        815.3 |               58.5 |      367 |
| forum Dual Momentum with Out Days - QuantConnect.com     | b3e5c2897b | daily        |       -5.9 |   -0.6 |   22   |  -31.5 |   -6.6 |   -5.4 |    0.2 |        736.5 |               44.3 |    23344 |
| forum Dual Momentum with Out Days - QuantConnect.com     | 36bb0852c1 | daily        |       -6.2 |    5.6 |   62.1 |  -28.3 |  -17   |  -20.7 |  -10   |        727.8 |               62.5 |    19968 |
| forum Using Levered ETFs in IRA - 10 years - 24% CAGR, 1 | 9fc9eff0f1 | daily        |       -7.8 |   -0.3 |  -68.7 |   69.3 |    9.9 |   25.7 |   -8.7 |        666.4 |               70.7 |      703 |
| forum Dual Momentum with Out Days - QuantConnect.com     | b506967692 | daily        |       -8   |   -0.6 |   83.6 |  -29.5 |  -28.8 |  -26.1 |   -2.8 |        657.4 |               70.1 |      242 |
| forum Dual Momentum with Out Days - QuantConnect.com     | da872fd8d4 | daily        |       -8   |   -0.6 |   83.6 |  -29.5 |  -28.8 |  -26.1 |   -2.8 |        657.4 |               70.1 |      242 |
| forum Dual Momentum with Out Days - QuantConnect.com     | b1be3ade25 | daily        |      -10   |   -0.6 |   22   |  -31.5 |  -21.2 |  -15.4 |    6.3 |        589.2 |               59.8 |   116784 |
| forum Using Levered ETFs in IRA - 10 years - 24% CAGR, 1 | bfe58a2e21 | daily        |      -10.2 |    1.4 |  -73.2 |   74.1 |   32.1 |    2.6 |   -8.7 |        585.3 |               75.2 |      580 |
| forum Dual Momentum with Out Days - QuantConnect.com     | 2d96c1b584 | daily        |      -10.7 |   -0.6 |   22   |  -31.5 |  -26.5 |  -13   |    6.7 |        567.4 |               61.3 |   115800 |
| forum Dual Momentum with Out Days - QuantConnect.com     | 2b1fc4cda1 | daily        |      -10.7 |   -0.6 |   22   |  -31.5 |  -26.5 |  -13   |    6.7 |        567.4 |               61.3 |   115800 |
| forum Dual Momentum with Out Days - QuantConnect.com     | 785bd73267 | daily        |      -12.1 |    3.1 |   41.3 |  -45.5 |  -17.9 |  -19.8 |    0.2 |        523.9 |               73   |    34113 |
| forum Dual Momentum with Out Days - QuantConnect.com     | 94c1b405ec | daily        |      -12.1 |    3.1 |   41.3 |  -45.5 |  -17.9 |  -19.8 |    0.2 |        523.9 |               73   |    34113 |
| forum Dual Momentum with Out Days - QuantConnect.com     | 18bc21a9ac | daily        |      -13.9 |   -0.4 |   66.2 |  -44.3 |  -25.7 |  -25.7 |   -7.2 |        472.6 |               77.8 |      675 |
| forum Amazing returns  superior stock selection strateg  | fe719d4b67 | daily        |      -17.4 |   -5.4 |   -8   |  -21   |  -18.1 |  -10.3 |  -23.9 |        384.4 |               61.6 |     1783 |
| forum Amazing returns  superior stock selection strateg  | 8937472c3f | daily        |      -17.5 |   -1.6 |  -76.2 |   96.6 |   21.6 |   -7.1 |  -26.6 |        382   |               79.6 |       90 |
| forum Amazing returns  superior stock selection strateg  | 55ba6bdbeb | daily        |      -18.2 |    1.5 |  -86   |   71.4 |   29.7 |   27.8 |   -9.3 |        365.5 |               91.5 |      156 |
| forum Amazing returns  superior stock selection strateg  | ed03383e2f | daily        |      -19.2 |    2.1 |  -53.5 |  -18.9 |   25.8 |  -19.4 |  -11.7 |        344.8 |               77.3 |       59 |
| forum Dual Momentum with Out Days - QuantConnect.com     | d71833616f | daily        |      -21.1 |   -5.3 |    7.1 |  -39.1 |  -30.6 |  -22.6 |   -7.8 |        305.9 |               74.1 |      306 |
| forum Amazing returns  superior stock selection strateg  | 42cb0e7aea | daily        |      -22.7 |    3.4 |  -62.6 |   -8.4 |  -13   |    5.6 |  -15.2 |        276.1 |               78.3 |       13 |
| forum Amazing returns  superior stock selection strateg  | 4115ee0aa3 | daily        |      -25.3 |   -2.8 |  -57.5 |  -22.3 |  -37.7 |   -5.8 |   23.3 |        232.5 |               85.6 |      358 |
| forum Amazing returns  superior stock selection strateg  | 2b54135926 | daily        |      -25.3 |   -2.8 |  -57.5 |  -22.3 |  -37.7 |   -5.8 |   23.3 |        232.5 |               85.6 |      358 |
| forum Amazing returns  superior stock selection strateg  | a424f0f66c | daily        |      -30.1 |   -2.9 |  -81.1 |   13.9 |   29.1 |  -15.9 |  -26.4 |        167.4 |               87.3 |      107 |
| forum Amazing returns  superior stock selection strateg  | d510466b31 | daily        |      -30.2 |   -2.9 |  -81.6 |   13.9 |   29.1 |  -13.5 |  -27.2 |        165.2 |               87.3 |      112 |
| forum Amazing returns  superior stock selection strateg  | ca58686291 | daily        |      -35.2 |    2.1 |  -71.7 |  -37.2 |  -21   |   -2.3 |  -18.3 |        114.6 |               91.8 |        7 |
| forum Amazing returns  superior stock selection strateg  | 84f8a4778f | daily        |      -39.1 |   -6.2 |  -60.2 |    3.1 |  -30.5 |  -43   |  -44.9 |         84   |               97.6 |       70 |

## forex

| name                                                                       | variant   | resolution   |   cagr_pct |   2021 |   2022 |   2023 |   2024 |   2025 |   2026 |   final_usdt |   max_drawdown_pct |   trades |
|:---------------------------------------------------------------------------|:----------|:-------------|-----------:|-------:|-------:|-------:|-------:|-------:|-------:|-------------:|-------------------:|---------:|
| Forex Momentum                                                             | d9f904bb  | daily        |        0.3 |    0.1 |    6.3 |   -1.6 |   -0.9 |   -1.7 |   -0.4 |       1016   |               16.4 |       34 |
| Forex Momentum                                                             | d9f904bb  | hour         |        0.1 |    0   |    5.7 |   -2.5 |   -1   |   -1   |   -0.5 |       1005.6 |               17.7 |       31 |
| The Dynamic Breakout II Strategy                                           | 9b315be0  | daily        |        0   |    0   |    0   |    0   |    0   |    0   |    0   |       1000   |                0   |        0 |
| The Dynamic Breakout II Strategy                                           | 5d238a74  | daily        |       -0.4 |    0   |    0   |   -2   |    0   |    0   |    0   |        980.4 |                2.7 |        2 |
| Risk Premia in Forex Markets                                               | d640f4ec  | hour         |       -1.3 |   -2.5 |    1.9 |   -6.5 |    4.3 |   -0.8 |   -2.2 |        938.9 |               12.7 |      371 |
| The Dynamic Breakout II Strategy                                           | 9b315be0  | hour         |       -2.6 |    0   |    1.2 |   -5.1 |   -7.3 |   -1   |   -0.8 |        874.8 |               21.4 |       44 |
| The Momentum Strategy Based on the Low Frequency Component of Forex Market | 17c90cb9  | daily        |       -2.9 |    0   |  -15.1 |    4.8 |    6.6 |   -9.3 |    0.1 |        861.7 |               20.8 |       11 |
| The Dynamic Breakout II Strategy                                           | 5d238a74  | hour         |       -3.8 |    0   |   -5.4 |   -8.4 |   -1.3 |   -2.5 |   -1.2 |        824.1 |               18.5 |       46 |
| Risk Premia in Forex Markets                                               | d640f4ec  | daily        |       -4.6 |   -2.8 |  -16.8 |   -4.7 |    7.2 |   -3.1 |   -1.6 |        789   |               23.6 |      371 |
| The Momentum Strategy Based on the Low Frequency Component of Forex Market | 17c90cb9  | hour         |      -10.8 |   -1.6 |  -14.6 |   -4.9 |  -15.1 |   -7.4 |   -9.9 |        566.2 |               44.4 |      128 |

## Neatliko nė vieno sandorio

Dažniausia priežastis: strategija prekiauja dienos viduryje ir tikrina minutines/valandines kainas, kurių šiems ETF neturime (reikėtų IBKR duomenų).

- F9632 forum Amazing returns  superior stock selection strateg 68267ac216 daily
- F9632 forum Amazing returns  superior stock selection strateg 9edefa25d1 daily
- 1029 Optimal Pairs Trading e9e74232 hour
- F9632 forum Amazing returns  superior stock selection strateg 668f08eb95 daily
- F9632 forum Amazing returns  superior stock selection strateg d7eb6b2089 daily
- F10039 forum Dual Momentum with Out Days - QuantConnect.com 3aa1830197 daily
- F9632 forum Amazing returns  superior stock selection strateg 1bb502e471 daily
- F9632 forum Amazing returns  superior stock selection strateg 8e5ac08df2 daily
- F9632 forum Amazing returns  superior stock selection strateg 4d3c02f3fc daily
- F9632 forum Amazing returns  superior stock selection strateg 665fbb24e9 daily
- F9632 forum Amazing returns  superior stock selection strateg 6c7e6f68cf daily
- 04 The Dynamic Breakout II Strategy 9b315be0 daily
- F9632 forum Amazing returns  superior stock selection strateg 73c23e66bd daily

## Nepavyko paleisti

- 02_83b5f8ca_daily
- 02_83b5f8ca_hour
- 1025_aeec93d6_daily
- 1031_638b6281_daily
- 1031_638b6281_hour
- F10039_5343b054aa_daily
- F7708_b4e2139e17_daily