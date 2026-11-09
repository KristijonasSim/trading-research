#!/bin/bash
# run all testable OctoBot profiles on one group, skip finished ones
cd "$(dirname "$0")/.."
G=$1
for P in daily_trading dip_analyser grid_trading trailing_grid_trading index_trading smart_dca staggered_orders_trading; do
  [ -f results/raw/${P}__${G}/summary.json ] && continue
  echo "$(date +%T) start $P $G"
  timeout 21600 .venv/bin/python scripts/run_bt.py $P $G > logs/bt_${P}__${G}.log 2>&1
  echo "$(date +%T) done $P $G exit=$?"
done
