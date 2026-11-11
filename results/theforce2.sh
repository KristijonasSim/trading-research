cd /home/kristijonas/Desktop/trading-research/freqtrade
for fee in 0.0015 0.002; do
 for g in btc_eth alts10; do
  if [ $g = btc_eth ]; then P="BTC/USDT ETH/USDT"; else P="XRP/USDT BNB/USDT SOL/USDT DOGE/USDT ADA/USDT TRX/USDT LINK/USDT AVAX/USDT LTC/USDT DOT/USDT"; fi
  d=results/validate50/fee_TheForce_${g}_$fee; mkdir -p $d
  docker run --rm --network none --memory 8g --user "$(id -u):$(id -g)" -v "$PWD/user_data:/freqtrade/user_data:ro" -v "$PWD/config_spot.json:/freqtrade/config.json:ro" \
   -v "$PWD/docker_offline:/offline:ro" -e PYTHONPATH=/offline -v "$PWD/$d:/out" freqtrade-research:latest backtesting --userdir /freqtrade/user_data -c /freqtrade/config.json \
   --strategy-path /freqtrade/user_data/strategies/validate50 --strategy TheForce --timerange 20211108-20261108 --timeframe 15m --pairs $P --max-open-trades $(echo $P|wc -w) \
   --fee $fee --export trades --backtest-directory /out --cache none > $d/log.txt 2>&1
  echo "fee=$fee $g: $(grep 'CAGR %' $d/log.txt | tail -1 | tr -s ' │' ' ') | $(grep 'Max % of account underwater' $d/log.txt | tail -1 | tr -s ' │' ' ')"
 done
done
BATCH=batch50i .venv/bin/python oos_batch.py TheForce:btc_eth TheForce:alts10
echo T2DONE
