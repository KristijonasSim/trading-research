#!/bin/bash
cd "$(dirname "$0")/.."
TR=20230101-20260101 ./validate_g.sh x "Ichimoku_v16:1d:BTC/USDT ETH/USDT" "Ichimoku_v2:4h:BTC/USDT ETH/USDT"
TR=20250101-20250701 ./validate_g.sh x "GodStraNew7:5m:XRP/USDT BNB/USDT SOL/USDT DOGE/USDT ADA/USDT TRX/USDT LINK/USDT AVAX/USDT LTC/USDT DOT/USDT"
echo LA_DONE
MEM=5g ./detail.sh Ichimoku_v16 1d 1h btc_eth
MEM=5g ./detail.sh Ichimoku_v2 4h 5m btc_eth
MEM=6g TAG=_fee15 EXTRA="--fee 0.0015" ./detail.sh GodStraNew7 5m 5m alts10
echo DETAIL_DONE
BATCH=batchM6 .venv/bin/python oos_batch.py Ichimoku_v16:btc_eth Ichimoku_v2:btc_eth GodStraNew7:alts10 GodStraNew7:btc_eth
echo CHECK_DONE
