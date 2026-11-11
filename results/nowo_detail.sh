cd /home/kristijonas/Desktop/trading-research/freqtrade
for g in btc_eth alts10; do
  if [ $g = btc_eth ]; then P="BTC/USDT ETH/USDT"; else P="XRP/USDT BNB/USDT SOL/USDT DOGE/USDT ADA/USDT TRX/USDT LINK/USDT AVAX/USDT LTC/USDT DOT/USDT"; fi
  n=$(echo $P | wc -w); d=results/validate50/detail_$g; mkdir -p $d
  docker run --rm --network none --memory 10g --user "$(id -u):$(id -g)" \
    -v "$PWD/user_data:/freqtrade/user_data:ro" -v "$PWD/config_spot.json:/freqtrade/config.json:ro" \
    -v "$PWD/docker_offline:/offline:ro" -e PYTHONPATH=/offline -v "$PWD/$d:/out" \
    freqtrade-research:latest backtesting --userdir /freqtrade/user_data -c /freqtrade/config.json \
    --strategy-path /freqtrade/user_data/strategies/validate50 --strategy NowoIchimoku1hV2 \
    --timerange 20211108-20261108 --timeframe 1h --timeframe-detail 5m --pairs $P --max-open-trades $n \
    --export trades --backtest-directory /out --cache none 2>&1 | grep -E "TOTAL|Max % of account|CAGR|Total profit %|ERROR" | head -8
  echo "== $g done"
done
