#!/bin/bash
# Visos kandidatės 2020-01-01 – 2026-11-08, eksportuojami sandoriai -> results/combo/<vardas>/
cd "$(dirname "$0")/../.."
ALTS="XRP/USDT BNB/USDT SOL/USDT DOGE/USDT ADA/USDT TRX/USDT LINK/USDT AVAX/USDT LTC/USDT DOT/USDT"
run() { name=$1; cfg=$2; tf=$3; pairs=$4; extra=$5; out=results/combo/$name; mkdir -p $out
  [ -n "$(ls $out/*.zip 2>/dev/null)" ] && { echo "skip $name"; return; }
  dd=""; [ "$cfg" = config_futures.json ] && dd="-v $PWD/fut_data:/freqtrade/fut_data:ro"
  dir=""; [ "$cfg" = config_futures.json ] && dir="--datadir /freqtrade/fut_data/binance"
  docker run --rm --network none --memory 24g --user "$(id -u):$(id -g)" -v "$PWD/user_data:/freqtrade/user_data:ro" $dd -v "$PWD/$cfg:/freqtrade/config.json:ro" -v "$PWD/docker_offline:/offline:ro" -e PYTHONPATH=/offline -v "$PWD/$out:/freqtrade/user_data/backtest_results" freqtrade-research:latest backtesting --userdir /freqtrade/user_data $dir -c /freqtrade/config.json --strategy-path /freqtrade/user_data/strategies/combo --strategy $name --timeframe $tf --timerange 20200101-20261108 --pairs $pairs --dry-run-wallet 10000 --export trades $extra > $out/log.txt 2>&1
  echo "$name: $(grep -E 'CAGR' $out/log.txt | head -1 | tr -s ' ')"; }
FUT=$(echo $ALTS | sed 's#/USDT#/USDT:USDT#g')
run EI3F_L1 config_futures.json 5m "$FUT"
run EI3F_L2 config_futures.json 5m "$FUT"
run EI3F_L3 config_futures.json 5m "$FUT"
run RegimeFilterStrategy config_futures.json 1h "$FUT"
for s in XSMomentumRotation MACDVStrategy Aberration TrendVolTarget; do run $s config_spot.json 1d "BTC/USDT ETH/USDT" "--max-open-trades 2"; done
run EMAPriceCrossoverWithTreshold config_spot.json 1h "BTC/USDT ETH/USDT" "--max-open-trades 2"
run DualThrust config_spot.json 5m "BTC/USDT ETH/USDT" "--max-open-trades 2"
run KeltnerRSI config_spot.json 1d "$ALTS"
for s in NASOSv5_mod3 BearBull3 DS_Green_5m NS4_dca abbasPublic BSS2b; do run $s config_spot.json 5m "$ALTS"; done
echo COMBO_DONE
