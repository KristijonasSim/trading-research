#!/bin/bash
# Dry-run botai (be API raktų, virtualūs 1000 USDT kiekvienam). Paleisti: bash dryrun/start.sh [vardas...]
# Žiūrėti: docker logs -f dry_<vardas>; rezultatai: dryrun/<vardas>/tradesv3.dryrun.sqlite; stabdyti: docker rm -f dry_<vardas>
cd "$(dirname "$0")"
for n in ${@:-aberration dualthrust ema800 funding nasos ei3v2}; do
  docker rm -f dry_$n >/dev/null 2>&1
  docker run -d --name dry_$n --restart unless-stopped --memory 2g --user "$(id -u):$(id -g)" \
    -v "$PWD/$n:/freqtrade/user_data" \
    freqtrade-research:latest trade --userdir /freqtrade/user_data -c /freqtrade/user_data/config.json \
    --strategy-path /freqtrade/user_data/strategies --logfile /freqtrade/user_data/bot.log
done
