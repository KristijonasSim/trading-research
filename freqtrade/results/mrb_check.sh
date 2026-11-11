#!/bin/bash
cd "$(dirname "$0")/.."
TR=20220101-20260101 ./validate_g.sh x "MomentumRegimeBasket:1d:BTC/USDT ETH/USDT"
echo LA_DONE
BATCH=batchM2 .venv/bin/python oos_batch.py MomentumRegimeBasket:btc_eth MomentumRegimeBasket:alts10
echo OOS_DONE
echo CHECK_DONE
