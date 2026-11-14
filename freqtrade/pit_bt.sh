#!/bin/bash
# Point-in-time backtestas: 2021-11 top 20 be BTC/ETH (su LUNA iki žlugimo, FTT, MATIC) – išgyvenusiųjų patikra.
# pit_bt.sh <Strategija> [timeframe-detail|none] [timerange]
cd "$(dirname "$0")"
S=$1; DT=${2:-none}; TR=${3:-20211108-20261108}
P="BNB/USDT SOL/USDT ADA/USDT XRP/USDT DOT/USDT DOGE/USDT AVAX/USDT LUNA/USDT SHIB/USDT MATIC/USDT LTC/USDT LINK/USDT UNI/USDT ALGO/USDT BCH/USDT ATOM/USDT FTT/USDT TRX/USDT"
d=results/pit/${S}_${DT}; mkdir -p $d
docker run --rm --network none --memory ${MEM:-12g} --user "$(id -u):$(id -g)" \
  -v "$PWD/user_data:/freqtrade/user_data:ro" -v "$PWD/pitdata:/pitdata:ro" -v "$PWD/${CFG:-config_spot.json}:/freqtrade/config.json:ro" \
  -v "$PWD/docker_offline_pit:/offline:ro" -e PYTHONPATH=/offline -v "$PWD/$d:/out" \
  freqtrade-research:latest backtesting --userdir /freqtrade/user_data -c /freqtrade/config.json --datadir /pitdata/binance \
  --strategy-path /freqtrade/user_data/strategies/validate50 --strategy $S \
  --timerange $TR $([ $DT = none ] || echo --timeframe-detail $DT) --pairs $P --max-open-trades ${MOT:-18} \
  --export trades --backtest-directory /out --cache none > $d/log.txt 2>&1
echo "$S PIT top20 detail=$DT $TR mot=${MOT:-18}: $(grep -E 'CAGR %' $d/log.txt | tail -1 | tr -s ' │' ' ') | DD: $(grep -E 'Max % of account underwater' $d/log.txt | tail -1 | tr -s ' │' ' ')" | tee -a results/pit/pit.log
