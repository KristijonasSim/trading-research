cd /home/kristijonas/Desktop/trading-research/freqtrade
./validate_g.sh x "NowoIchimoku1hV2:1h:BTC/USDT ETH/USDT SOL/USDT XRP/USDT DOGE/USDT"
BATCH=batch50h .venv/bin/python oos_batch.py NowoIchimoku1hV2:alts10 NowoIchimoku1hV2:btc_eth
echo CHECK_DONE
