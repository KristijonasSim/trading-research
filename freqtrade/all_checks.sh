#!/usr/bin/env bash
# lookahead + 1m detail (2020) + 2018 top9 for NAMES (5m alts) and BTCETH (1d) — offline Docker
cd "$(dirname "$0")"
A="XRP/USDT BNB/USDT SOL/USDT DOGE/USDT ADA/USDT TRX/USDT LINK/USDT AVAX/USDT LTC/USDT DOT/USDT"
dk() { local tag=$1; shift; mkdir -p results/detail/$tag
  docker run --rm --network none --memory 12g --user "$(id -u):$(id -g)" -v "$PWD/user_data:/freqtrade/user_data:ro" \
  -v "$PWD/config_spot_market.json:/freqtrade/config.json:ro" -v "$PWD/docker_offline:/offline:ro" -e PYTHONPATH=/offline \
  -v "$PWD/results/detail/$tag:/freqtrade/user_data/backtest_results" freqtrade-research:latest "$@" --userdir /freqtrade/user_data \
  -c /freqtrade/config.json --strategy-path /freqtrade/user_data/strategies/validate50 2>&1 | grep -vE "chown|FutureWarning|import freqtrade.vendor"; }
for n in $BTCETH; do
  dk la_$n lookahead-analysis --strategy $n --timeframe 1d --timerange 20220101-20260101 --pairs BTC/USDT ETH/USDT --max-open-trades 2 > ../results/validation/${n}_batchM39.log
  echo "$n LA: $(grep -E "│ .*\.py" ../results/validation/${n}_batchM39.log | tr -s ' ')"; done
for n in $NAMES; do
  dk la_$n lookahead-analysis --strategy $n --timeframe 5m --timerange 20250101-20250701 --pairs $A --max-open-trades 5 > ../results/validation/${n}_batchM36.log
  echo "$n LA: $(grep -E "│ .*\.py" ../results/validation/${n}_batchM36.log | tr -s ' ') $(grep -c Error ../results/validation/${n}_batchM36.log)"
  for det in "" "--timeframe-detail 1m"; do
    echo "$n 2020 ${det:-plain}: $(dk d_$n backtesting --strategy $n --timeframe 5m --timerange 20200201-20201231 --pairs $A --max-open-trades 10 $det --export none | grep -E "CAGR|Absolute drawdown " | tr -s ' ' | tr '\n' ' ')"; done
  echo "$n top9: $(dk t9_$n backtesting --strategy $n --timeframe 5m --timerange 20180101-20211108 --pairs XRP/USDT LTC/USDT XLM/USDT ADA/USDT TRX/USDT NEO/USDT IOTA/USDT BNB/USDT ETC/USDT --max-open-trades 10 --export none | grep -E "CAGR|Absolute drawdown " | tr -s ' ' | tr '\n' ' ')"
done
echo CHECKS_DONE
