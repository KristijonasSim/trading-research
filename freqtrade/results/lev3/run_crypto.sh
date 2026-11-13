#!/bin/bash
# EI3v2 3x ir NASOSv5_mod3 5x, Binance futures 2020-01-01 – 2026-11-08: 10 altcoin'ų ir BTC+ETH
cd "$(dirname "$0")/../.."
A="XRP/USDT:USDT BNB/USDT:USDT SOL/USDT:USDT DOGE/USDT:USDT ADA/USDT:USDT TRX/USDT:USDT LINK/USDT:USDT AVAX/USDT:USDT LTC/USDT:USDT DOT/USDT:USDT"
B="BTC/USDT:USDT ETH/USDT:USDT"
for SL in EI3v2_tag_cofi_green:3 NASOSv5_mod3:5; do S=${SL%%:*}; L=${SL#*:}
  for G in alts10 btc_eth; do [ $G = alts10 ] && P=$A || P=$B; [ $G = alts10 ] && M=10 || M=2
    LEV=$L .venv/bin/freqtrade backtesting -c config_futures_market.json -s ${S}_Lev --strategy-path user_data/strategies/lev \
      --timerange 20200101-20261108 -p $P --max-open-trades $M --breakdown year > results/lev3/${G}_${S}_${L}x.log 2>&1 &
  done
done
wait; echo CRYPTO_DONE
