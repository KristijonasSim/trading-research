#!/bin/bash
# Laukia, kol baigsis queue7, tada paleidžia queue8
cd "$(dirname "$0")"
while [ ! -f results/queue7_done.txt ]; do sleep 300; done
./queue8.sh > results/queue8.out 2>&1
