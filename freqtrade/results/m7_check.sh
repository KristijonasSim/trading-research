#!/bin/bash
cd "$(dirname "$0")/.."
A="XRP/USDT BNB/USDT SOL/USDT DOGE/USDT ADA/USDT TRX/USDT LINK/USDT AVAX/USDT LTC/USDT DOT/USDT"
TR=20230101-20260101 ./validate_g.sh x "Ichimoku_v5:4h:$A" "Ichimoku_v8:4h:BTC/USDT ETH/USDT"
echo LA_DONE
MEM=6g ./detail.sh Ichimoku_v5 4h 5m alts10
MEM=5g ./detail.sh Ichimoku_v8 4h 5m btc_eth
echo DETAIL_DONE
BATCH=batchM7 .venv/bin/python oos_batch.py Ichimoku_v5:alts10 Ichimoku_v8:btc_eth
echo CHECK_DONE
