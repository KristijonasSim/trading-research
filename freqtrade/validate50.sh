#!/usr/bin/env bash
# Checks for the two best new strategies, in offline Docker (same sandbox as run_batch.py):
#  - ichiV1_fixed: ichiV1 without the Heikin-Ashi price overwrite, full 5-year backtest (BTC+ETH)
#  - lookahead-analysis + recursive-analysis for ichiV1 and EI3v2_tag_cofi_green
cd "$(dirname "$0")"
OUT=../results/validation; mkdir -p "$OUT" results/validate50
dk() { # name args...
  local name=$1; shift
  mkdir -p results/validate50/$name
  docker run --rm --network none --memory 6g --user "$(id -u):$(id -g)" \
    -v "$PWD/user_data:/freqtrade/user_data:ro" -v "$PWD/config_spot.json:/freqtrade/config.json:ro" \
    -v "$PWD/docker_offline:/offline:ro" -e PYTHONPATH=/offline \
    -v "$PWD/results/validate50/$name:/freqtrade/user_data/backtest_results" \
    freqtradeorg/freqtrade:stable "$@" --userdir /freqtrade/user_data -c /freqtrade/config.json \
    --strategy-path /freqtrade/user_data/strategies/validate50 2>&1 | grep -vE "FutureWarning|import freqtrade.vendor"
}
MAJ="BTC/USDT ETH/USDT"; ALT3="SOL/USDT XRP/USDT DOGE/USDT"
dk ichiV1_fixed_bt backtesting --strategy ichiV1_fixed --timerange 20211108-20261108 --pairs $MAJ \
   --max-open-trades 2 --export trades --backtest-directory /freqtrade/user_data/backtest_results --cache none \
   | tail -60 > $OUT/ichiV1_fixed_backtest.log
for s in "ichiV1:$MAJ" "EI3v2_tag_cofi_green:$ALT3"; do
  n=${s%%:*}; p=${s#*:}
  { echo "### lookahead-analysis $n"; dk la_$n lookahead-analysis --strategy $n --timerange 20250101-20250701 --pairs $p --max-open-trades 3 | tail -30
    echo "### recursive-analysis $n"; dk ra_$n recursive-analysis --strategy $n --timerange 20250101-20250301 --pairs ${p%% *} | tail -30
    echo VALIDATION_DONE; } > $OUT/${n}_batch50.log
done
echo ALL_DONE
