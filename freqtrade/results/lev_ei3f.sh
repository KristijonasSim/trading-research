#!/bin/bash
cd "$(dirname "$0")/.."
source <(sed -n 1,3p results/fut_check.sh)
for L in 1 2 3 4 5; do
  S=EI3F_L$L
  echo "### ${L}x"
  dk lev_$S backtesting --strategy $S --timeframe 5m --timerange 20200101-20261108 --pairs $PAIRS --breakdown year --export trades > results/lev_ei3f_$L.txt 2>&1; grep -E "CAGR|Absolute drawdown \(|Max % of account underwater \(|Total profit %|Final balance|Total/Daily|Liquidat" results/lev_ei3f_$L.txt; grep -A12 "YEAR STATS\|BREAKDOWN" results/lev_ei3f_$L.txt | grep -E "^│ *[0-9]{2}/[0-9]{2}/20|^│ *20[0-9][0-9]"
done
echo LEV_DONE
