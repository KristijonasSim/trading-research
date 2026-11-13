#!/usr/bin/env bash
# lookahead + recursive analysis for the two batch50g candidates (offline Docker)
cd "$(dirname "$0")"
OUT=../results/validation
dk() { local name=$1; shift; mkdir -p results/validate50/$name
  docker run --rm --network none --memory 8g --user "$(id -u):$(id -g)" \
    -v "$PWD/user_data:/freqtrade/user_data:ro" -v "$PWD/config_spot_market.json:/freqtrade/config.json:ro" \
    -v "$PWD/docker_offline:/offline:ro" -e PYTHONPATH=/offline \
    -v "$PWD/results/validate50/$name:/freqtrade/user_data/backtest_results" \
    freqtrade-research:latest "$@" --userdir /freqtrade/user_data -c /freqtrade/config.json \
    --strategy-path /freqtrade/user_data/strategies/validate50 2>&1 | grep -vE "FutureWarning|import freqtrade.vendor"; }
for s in "${@:2}"; do
  n=${s%%:*}; r=${s#*:}; tf=${r%%:*}; p=${r#*:}
  { echo "### lookahead-analysis $n"; dk la_$n lookahead-analysis --strategy $n --timeframe $tf --timerange ${TR:-20250101-20250701} --pairs $p --max-open-trades 3 | tail -30
    echo "### recursive-analysis $n"; dk ra_$n recursive-analysis --strategy $n --timeframe $tf --timerange 20250101-20250301 --pairs ${p%% *} | tail -30
    echo VALIDATION_DONE; } > $OUT/${n}_batchM14.log
done
echo ALL_DONE
