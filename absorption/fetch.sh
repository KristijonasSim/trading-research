#!/bin/bash
# Binance USDT-M futures 5m klines (su taker buy volume) iš data.binance.vision
cd data
for s in BTCUSDT ETHUSDT; do
  for y in 2021 2022 2023 2024 2025 2026; do for m in 01 02 03 04 05 06 07 08 09 10 11 12; do
    f=$s-5m-$y-$m.zip; [ -f $f ] && continue
    [ "$y$m" \> "202610" ] && continue
    curl -sf -O https://data.binance.vision/data/futures/um/monthly/klines/$s/5m/$f || echo "nėra $f"
  done; done
done
ls *.zip | wc -l
