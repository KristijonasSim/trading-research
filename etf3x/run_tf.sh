#!/usr/bin/env bash
# Same as run.sh, but with the strategy timeframe overridden to 1h / 4h / 1d
cd "$(dirname "$0")"
PAIRS=$(python3 -c "import json;print(' '.join(json.load(open('ft/pairs.json'))))"); N=$(echo $PAIRS | wc -w)
for tf in ${TFS:-1h 4h 1d}; do for s in ${STRATS:-EI3v2_tag_cofi_green E0V1E_DCA3}; do
  d=results/tf_${tf}${DETAIL:+_det}_$s; mkdir -p $d
  for cfg in config_3x.json config_3x_market.json; do
    docker run --rm --network none --memory 6g --user "$(id -u):$(id -g)" \
      -v "$PWD/../freqtrade/user_data:/freqtrade/user_data:ro" -v "$PWD/ft/$cfg:/freqtrade/config.json:ro" \
      -v "$PWD/ft/offline:/offline:ro" -e PYTHONPATH=/offline -v "$PWD/ft/data:/data:ro" \
      -v "$PWD/strategies_tf:/strats:ro" -v "$PWD/$d:/out" freqtrade-research:latest backtesting \
      --userdir /freqtrade/user_data -c /freqtrade/config.json --datadir /data/binance --strategy-path /strats \
      --strategy $s --timeframe $tf $DETAIL --timerange 20211108-20261108 --pairs $PAIRS --max-open-trades $N \
      --export trades --backtest-directory /out --cache none > $d/backtest.log 2>&1
    grep -q 'price_side = "other"' $d/backtest.log || break
  done
  echo "$tf $s: $(grep -E 'CAGR %' $d/backtest.log | head -1 | tr -s ' │' ' ') | $(grep -E 'Max % of account underwater ' $d/backtest.log | head -1 | tr -s ' │' ' ') | $(grep -E 'Total/Daily' $d/backtest.log | head -1 | tr -s ' │' ' ') $(grep -m1 -E 'Error|ERROR' $d/backtest.log | cut -c1-150)"
done; done
