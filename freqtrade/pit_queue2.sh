#!/bin/bash
cd "$(dirname "$0")"
until grep -q PIT_Q_DONE results/pit/pit.log 2>/dev/null; do sleep 30; done
for s in abbas NASMAO SMAO; do ./pit_bt.sh $s; done
echo PIT_Q2_DONE >> results/pit/pit.log
