#!/usr/bin/env bash
# 2018 top-9 coins (no survivorship), 2018-01-01..2021-11-08, offline Docker
cd "$(dirname "$0")"
P="XRP/USDT LTC/USDT XLM/USDT ADA/USDT TRX/USDT NEO/USDT IOTA/USDT BNB/USDT ETC/USDT"
for n in ${NAMES:-NASMAO SMAO abbas}; do mkdir -p results/detail/${n}_top9
  docker run --rm --network none --memory 24g --user "$(id -u):$(id -g)" -v "$PWD/user_data:/freqtrade/user_data:ro" \
    -v "$PWD/config_spot_market.json:/freqtrade/config.json:ro" -v "$PWD/docker_offline:/offline:ro" -e PYTHONPATH=/offline \
    -v "$PWD/results/detail/${n}_top9:/freqtrade/user_data/backtest_results" freqtrade-research:latest backtesting \
    --strategy $n --timeframe ${TF:-5m} --timerange 20180101-20211108 --pairs $P --max-open-trades 10 --breakdown year --userdir /freqtrade/user_data \
    -c /freqtrade/config.json --strategy-path /freqtrade/user_data/strategies/validate50 --export none 2>&1 \
    | grep -vE "chown|FutureWarning" | grep -E "CAGR|Absolute drawdown|Total profit %|Market change|^│ *(2018|2019|2020|2021)" > results/detail/${n}_top9.txt
  echo "== $n"; cat results/detail/${n}_top9.txt; done
echo TOP9_DONE
