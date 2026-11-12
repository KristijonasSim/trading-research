#!/bin/bash
cd "$(dirname "$0")/.."
A="XRP/USDT BNB/USDT SOL/USDT DOGE/USDT ADA/USDT TRX/USDT LINK/USDT AVAX/USDT LTC/USDT DOT/USDT"
TR=20250101-20250701 ./validate_g.sh x "ckNSJT_morning:5m:$A"
echo LA_DONE
MEM=6g TAG=_fee15 EXTRA="--fee 0.0015" ./detail.sh ckNSJT_morning 5m none alts10
echo DETAIL_DONE
BATCH=batchM8 .venv/bin/python oos_batch.py ckNSJT_morning:alts10
echo CHECK_DONE
