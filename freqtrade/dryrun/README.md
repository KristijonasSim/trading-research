# Dry-run botai (paleista 2026-11-14, šis kompiuteris)
Binance kainos gyvai, be API raktų, kiekvienam virtualūs 1000 USDT, BTC+ETH (nasos ir ei3v2 – 10 altcoin'ų, nuo 2026-11-14 01:23), Docker `--restart unless-stopped`.
| Botas | Strategija | Rinka | Backtestas 2021–26 |
|---|---|---|---|
| aberration | Aberration (1d) | spot, 0,1 % | +18,4 %/m., kritimas 28 % |
| dualthrust | DualThrust (5m + 1d) | spot, 0,1 % | +11,7 %/m., kritimas 12 % |
| ema800 | EMAPriceCrossoverWithTreshold (1h) | spot, 0,1 % | +21,4 %/m., kritimas 32 % (5m detalumas tas pats) |
| nasos | NASOSv5_mod3 (5m) | alts10 spot, 0,1 % | +18,3 %/m., kritimas 3 % (1m detalumas išlaiko) |
| ei3v2 | EI3v2_tag_cofi_green (5m) | alts10 spot, 0,1 % | ~+21 %/m. su 1m detalumu, kritimas ~26 % |
| funding | FundingContrarian (1d + funding) | futures 1x, 0,05 % | +26,5 %/m., kritimas 22 % |

Komandos: `bash freqtrade/dryrun/start.sh [vardas]` (paleisti/perkrauti), `python3 freqtrade/dryrun/status.py` (suvestinė), `docker logs -f dry_<vardas>`.
Pastaba: Aberration ir funding prekiauja retai (~8 ir ~18 sandorių per metus vienai monetai) – vertinti po 2–3 mėn.
