#!/usr/bin/env bash
# Compare backtest with/without finer timeframe-detail (offline Docker)
cd "$(dirname "$0")"
P="XRP/USDT BNB/USDT SOL/USDT DOGE/USDT ADA/USDT TRX/USDT LINK/USDT AVAX/USDT LTC/USDT DOT/USDT"
run() { local n=$1 tf=$2 tr=$3 det=$4 tag=$5; mkdir -p results/detail/${n}_$tag
  docker run --rm --network none --memory 24g --user "$(id -u):$(id -g)" -v "$PWD/user_data:/freqtrade/user_data:ro" \
    -v "$PWD/config_spot_market.json:/freqtrade/config.json:ro" -v "$PWD/docker_offline:/offline:ro" -e PYTHONPATH=/offline \
    -v "$PWD/results/detail/${n}_$tag:/freqtrade/user_data/backtest_results" freqtrade-research:latest backtesting \
    --strategy $n --timeframe $tf --timerange $tr --pairs $P --max-open-trades 10 $det --userdir /freqtrade/user_data \
    -c /freqtrade/config.json --strategy-path /freqtrade/user_data/strategies/validate50 --export none 2>&1 \
    | grep -E "TOTAL|Absolute drawdown|Total profit %" | head -4 > results/detail/${n}_$tag.txt
  echo "$n $tag: $(tr -s ' ' < results/detail/${n}_$tag.txt | tr '\n' ' ')"; }
for n in ${NAMES:-NASMAO SMAO abbas}; do run $n 5m 20200201-20201231 "" plain20; run $n 5m 20200201-20201231 "--timeframe-detail 1m" d1m20; done
echo ALL_DONE2
