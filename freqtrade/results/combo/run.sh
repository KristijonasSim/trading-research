#!/bin/bash
# EI3v2 ir E0V1E_DCA3 atskirai (spot, 0,1 %), sandoriai eksportuojami deriniui skaičiuoti
cd "$(dirname "$0")/../.."
FT=/home/kris/trading/ft-venv/bin/freqtrade
A="XRP/USDT BNB/USDT SOL/USDT DOGE/USDT ADA/USDT TRX/USDT LINK/USDT AVAX/USDT LTC/USDT DOT/USDT"
B="XRP/USDT LTC/USDT XLM/USDT ADA/USDT TRX/USDT NEO/USDT IOTA/USDT BNB/USDT ETC/USDT"
run() { # strat cfg period pairs tag
  $FT backtesting -c $2 -s $1 --strategy-path user_data/strategies/batch50 --timerange $3 -p $4 \
    --max-open-trades 10 --export trades --backtest-directory results/combo/$5_$1 > results/combo/$5_$1.log 2>&1; }
mkdir -p results/combo/{new,old}_{EI3v2_tag_cofi_green,E0V1E_DCA3}
run EI3v2_tag_cofi_green config_spot.json 20211108-20261108 "$A" new &
run E0V1E_DCA3 config_spot_market.json 20211108-20261108 "$A" new &
run EI3v2_tag_cofi_green config_spot.json 20180101-20211108 "$B" old &
run E0V1E_DCA3 config_spot_market.json 20180101-20211108 "$B" old &
wait
