#!/usr/bin/env bash
# Backtest the selected crypto strategies on synthetic 3x ETFs (offline Docker), 2021-11-08..2026-11-08
cd "$(dirname "$0")"; mkdir -p results
PAIRS=$(python3 -c "import json;print(' '.join(json.load(open('ft/pairs.json'))))")
N=$(echo $PAIRS | wc -w)
for s in EI3v2_tag_cofi_green E0V1E_DCA3; do
  for cfg in config_3x.json config_3x_market.json; do
    mkdir -p results/$s
    docker run --rm --network none --memory 6g --user "$(id -u):$(id -g)" \
      -v "$PWD/../freqtrade/user_data:/freqtrade/user_data:ro" -v "$PWD/ft/$cfg:/freqtrade/config.json:ro" \
      -v "$PWD/ft/offline:/offline:ro" -e PYTHONPATH=/offline -v "$PWD/ft/data:/data:ro" \
      -v "$PWD/strategies:/strats:ro" -v "$PWD/results/$s:/out" freqtrade-research:latest backtesting \
      --userdir /freqtrade/user_data -c /freqtrade/config.json --datadir /data/binance --strategy-path /strats \
      --strategy $s --timerange 20211108-20261108 --pairs $PAIRS --max-open-trades $N \
      --export trades --backtest-directory /out --cache none > results/$s/backtest.log 2>&1
    grep -q 'price_side = "other"' results/$s/backtest.log || break
  done
  echo "$s done"
done
