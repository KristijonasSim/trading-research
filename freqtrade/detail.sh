#!/bin/bash
# backtest with --timeframe-detail: detail.sh <Strategy> <timeframe> <detail_tf> <group> [timerange]
cd "$(dirname "$0")"
S=$1; TF=$2; DT=$3; g=$4; TR=${5:-20211108-20261108}
if [ $g = btc_eth ]; then P="BTC/USDT ETH/USDT"; else P="XRP/USDT BNB/USDT SOL/USDT DOGE/USDT ADA/USDT TRX/USDT LINK/USDT AVAX/USDT LTC/USDT DOT/USDT"; fi
n=$(echo $P | wc -w); d=results/validate50/detail_${S}_${g}_${DT}${TAG}; mkdir -p $d
docker run --rm --network none --memory ${MEM:-8g} --user "$(id -u):$(id -g)" \
  -v "$PWD/user_data:/freqtrade/user_data:ro" -v "$PWD/${CFG:-config_spot.json}:/freqtrade/config.json:ro" \
  -v "$PWD/docker_offline:/offline:ro" -e PYTHONPATH=/offline -v "$PWD/$d:/out" \
  freqtrade-research:latest backtesting --userdir /freqtrade/user_data -c /freqtrade/config.json \
  --strategy-path /freqtrade/user_data/strategies/validate50 --strategy $S \
  --timerange $TR --timeframe $TF $([ $DT = none ] || echo --timeframe-detail $DT) --pairs $P --max-open-trades $n \
  --export trades --backtest-directory /out --cache none $EXTRA > $d/log.txt 2>&1
echo "$S $g detail=$DT $TR: $(grep -E 'CAGR %' $d/log.txt | tail -1 | tr -s ' │' ' ') | DD: $(grep -E 'Max % of account underwater' $d/log.txt | tail -1 | tr -s ' │' ' ')"
