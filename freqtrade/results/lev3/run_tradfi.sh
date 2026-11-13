#!/bin/bash
# EI3v2 3x ir NASOSv5_mod3 5x ant aukso / NAS100 / S&P 500 (Dukascopy 5m, 2016-02 – 2026-11), visas balansas į 1 instrumentą
cd "$(dirname "$0")/../.."
for I in XAU NAS100 SPX500; do
 for SL in EI3v2_tag_cofi_green:3 NASOSv5_mod3:5; do S=${SL%%:*}; L=${SL#*:}
  LEV=$L .venv/bin/freqtrade backtesting -c config_futures_market.json -s ${S}_Lev --strategy-path user_data/strategies/lev \
    --datadir ../tradfi5m/ft_$I/binance --timerange 20160201-20261111 -p ADA/USDT:USDT --max-open-trades 1 \
    --breakdown year --export trades --backtest-filename results/lev3/${I}_${S}_${L}x.json > results/lev3/${I}_${S}_${L}x.log 2>&1 &
 done
done
wait
echo TRADFI_DONE
