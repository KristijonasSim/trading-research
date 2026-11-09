#!/bin/bash
# run every line "folder|variant|res" of jobs.txt, N in parallel, skip finished
cd "$(dirname "$0")/.."
N=${1:-6}
while IFS='|' read f v r; do
  n="${f%% *}_${v}_${r}"
  [ -f "results/raw/$n/summary.json" ] || printf '%s\0%s\0%s\0' "$f" "$v" "$r"
done < "${2:-scripts/jobs.txt}" | xargs -0 -n 3 -P "$N" bash -c '.venv/bin/python scripts/run_lean.py "$0" "$1" "$2" > /dev/null 2>&1; echo "$(date +%T) $0 $1 $2 exit=$?"'
