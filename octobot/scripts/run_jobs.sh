#!/bin/bash
# run "profile group" lines from a file, N in parallel, skip finished
cd "$(dirname "$0")/.."
F=$1; N=${2:-6}
grep -v '^$' "$F" | while read P G; do
  [ -f "results/raw/${P}__${G}/summary.json" ] || echo "$P $G"
done | xargs -P "$N" -L 1 bash -c 'echo "$(date +%T) start $0 $1"; timeout 21600 .venv/bin/python scripts/run_bt.py $0 $1 > "logs/bt_$0__$1.log" 2>&1; echo "$(date +%T) done $0 $1 exit=$?"'
