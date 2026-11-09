#!/usr/bin/env bash
# Validation of the best strategies: lookahead + recursive analysis.
# Every check writes its own log into ../results/validation/ and is skipped
# if that log already says it finished, so the script can be re-run after a reboot.
cd "$(dirname "$0")"
FT=.venv/bin/freqtrade
OUT=../results/validation
mkdir -p "$OUT"
PROG=../results/PROGRESS.md

ALTS3="SOL/USDT XRP/USDT DOGE/USDT"
MAJ="BTC/USDT ETH/USDT"

log() { echo "- $(date '+%Y-%m-%d %H:%M') $*" >> "$PROG"; }

check() { # name mode strategy timerange pairs...
  local name=$1 mode=$2 strat=$3 tr=$4; shift 4
  local f="$OUT/$name.log"
  if grep -q "VALIDATION_DONE" "$f" 2>/dev/null; then return; fi
  local cfg=config_spot.json; [ "$mode" = futures ] && cfg=config_futures.json
  local pairs=("$@")
  [ "$mode" = futures ] && pairs=("${pairs[@]/%/:USDT}")
  {
    echo "### lookahead-analysis $strat $tr ${pairs[*]}"
    timeout 3h $FT lookahead-analysis --userdir user_data -c $cfg \
      --strategy-path user_data/strategies/$mode --strategy "$strat" \
      --timerange "$tr" --pairs "${pairs[@]}" --max-open-trades ${#pairs[@]} 2>&1 \
      | grep -vE "FutureWarning|import freqtrade.vendor" | tail -40
    echo
    echo "### recursive-analysis $strat"
    timeout 2h $FT recursive-analysis --userdir user_data -c $cfg \
      --strategy-path user_data/strategies/$mode --strategy "$strat" \
      --timerange "$tr" --pairs "${pairs[0]}" 2>&1 \
      | grep -vE "FutureWarning|import freqtrade.vendor" | tail -40
    echo "VALIDATION_DONE"
  } > "$f"
  local verdict
  verdict=$(grep -E "│ .*\.py" "$f" | head -1 | awk -F'│' '{print $4}' | tr -d ' ')
  log "validation $name: lookahead bias = ${verdict:-?} (log: results/validation/$name.log)"
}

check NFI_X8_alts        spot    NostalgiaForInfinityX8    20250101-20250701 $ALTS3
check CombinedBinHAndCluc_alts spot CombinedBinHAndCluc    20250101-20260101 $ALTS3
check ReinforcedAverage_alts spot  ReinforcedAverageStrategy 20240101-20260101 $ALTS3
check Low_BB_alts        spot    Low_BB                    20250101-20250401 $ALTS3
check BinHV45_btc_eth    spot    BinHV45                   20250101-20250401 $MAJ
check UniversalMACD_btc_eth spot UniversalMACD             20250101-20260101 $MAJ
check VolatilitySystem_alts futures VolatilitySystem       20250101-20260101 $ALTS3
ALTS5="SOL/USDT XRP/USDT DOGE/USDT ADA/USDT LINK/USDT"
check NFI_X8_btc_eth_2024 spot   NostalgiaForInfinityX8    20240101-20240701 $MAJ
check NFI_X8_alts5_2023  spot    NostalgiaForInfinityX8    20230101-20230701 $ALTS5
check Low_BB_alts5_2024  spot    Low_BB                    20240101-20250101 $ALTS5
check BinHV45_alts5_2024 spot    BinHV45                   20240101-20250101 $ALTS5
ALTS10="XRP/USDT BNB/USDT SOL/USDT DOGE/USDT ADA/USDT TRX/USDT LINK/USDT AVAX/USDT LTC/USDT DOT/USDT"
check NFI_X8_alts10_2025 spot NostalgiaForInfinityX8 20250101-20260101 $ALTS10
echo "ALL_VALIDATION_DONE"
