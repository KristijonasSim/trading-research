#!/bin/bash
# Abu botai ant 30 altcoin'ų (2021 m. lapkr. top 32 be BTC/ETH; MATIC, FTM duomenų nėra), max 10 pozicijų
cd "$(dirname "$0")/../.."
FT=/home/kris/trading/ft-venv/bin/freqtrade
A="XRP/USDT BNB/USDT SOL/USDT DOGE/USDT ADA/USDT TRX/USDT LINK/USDT AVAX/USDT LTC/USDT DOT/USDT SHIB/USDT LUNA/USDT UNI/USDT ALGO/USDT BCH/USDT VET/USDT XLM/USDT ATOM/USDT AXS/USDT ICP/USDT FTT/USDT FIL/USDT ETC/USDT THETA/USDT HBAR/USDT MANA/USDT SAND/USDT EGLD/USDT XTZ/USDT NEAR/USDT"
run() { mkdir -p results/combo/$4_$1
  $FT backtesting -c $2 -s $1 --strategy-path user_data/strategies/batch50 --timerange 20211108-20261108 -p $A \
    --max-open-trades $3 --breakdown year --export trades --backtest-directory results/combo/$4_$1 > results/combo/$4_$1.log 2>&1; }
run EI3v2_tag_cofi_green config_spot.json 10 t30 &
run E0V1E_DCA3 config_spot_market.json 10 t30 &
run EI3v2_tag_cofi_green config_spot.json 30 t30m30 &
run E0V1E_DCA3 config_spot_market.json 30 t30m30 &
wait
