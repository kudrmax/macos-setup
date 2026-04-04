#!/bin/bash
input=$(cat)

MODEL=$(echo "$input" | jq -r '.model.display_name // "?"')
PCT=$(echo "$input" | jq -r '.context_window.used_percentage // 0' | cut -d. -f1)
DURATION_MS=$(echo "$input" | jq -r '.cost.total_duration_ms // 0')
FIVE_H=$(echo "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty')
FIVE_H_RESETS_AT=$(echo "$input" | jq -r '.rate_limits.five_hour.resets_at // empty')
DIR=$(echo "$input" | jq -r '.workspace.current_dir // "?"')
DIR="${DIR##*/}"

# Progress bar: make_bar PCT WIDTH
make_bar() {
  local pct=$1
  local width=$2
  local filled=$((pct * width / 100))
  [ "$filled" -gt "$width" ] && filled=$width
  local empty=$((width - filled))
  local bar=""
  [ "$filled" -gt 0 ] && printf -v f "%${filled}s" && bar="${f// /▓}"
  [ "$empty" -gt 0 ] && printf -v e "%${empty}s" && bar="${bar}${e// /░}"
  echo "$bar"
}

# Color by percentage
color_by_pct() {
  local pct=$1
  if [ "$pct" -ge 90 ]; then echo '\033[31m'
  elif [ "$pct" -ge 70 ]; then echo '\033[33m'
  else echo '\033[32m'; fi
}

# Session elapsed minutes
MINS=$((DURATION_MS / 60000))

# Context bar
CTX_CLR=$(color_by_pct "$PCT")
CTX_BAR=$(make_bar "$PCT" 10)

# 5h rate limit section
RATE_SECTION=""
if [ -n "$FIVE_H" ]; then
  FIVE_H_INT=${FIVE_H%%.*}

  # Elapsed time in 5h window from resets_at
  WINDOW_ELAPSED_MINS=0
  if [ -n "$FIVE_H_RESETS_AT" ]; then
    NOW=$(date +%s)
    WINDOW_START=$((FIVE_H_RESETS_AT - 18000))
    WINDOW_ELAPSED_SECS=$((NOW - WINDOW_START))
    WINDOW_ELAPSED_MINS=$((WINDOW_ELAPSED_SECS / 60))
    [ "$WINDOW_ELAPSED_MINS" -lt 0 ] && WINDOW_ELAPSED_MINS=0
    [ "$WINDOW_ELAPSED_MINS" -gt 300 ] && WINDOW_ELAPSED_MINS=300
  fi

  # Budget pace emoji: compare actual 5h usage vs expected at elapsed window time
  # Formula: expected_pct = elapsed_mins / 300 * 100
  EXPECTED_PCT=$((WINDOW_ELAPSED_MINS * 100 / 300))
  DIFF=$((FIVE_H_INT - EXPECTED_PCT))
  DIFF_ABS=${DIFF#-}
  [ "$DIFF" -gt 0 ] && DIFF_SIGNED="+${DIFF}" || DIFF_SIGNED="${DIFF}"
  if [ "$DIFF_ABS" -le 2 ]; then
    EMOJI="🔥"   # on pace (within ±2%)
  elif [ "$DIFF" -lt -2 ]; then
    EMOJI="🧊"   # spending less than expected — ahead of budget
  else
    EMOJI="🚨"   # spending more than expected — burning too fast
  fi

  # 5h usage bar
  RATE_CLR=$(color_by_pct "$FIVE_H_INT")
  RATE_BAR=$(make_bar "$FIVE_H_INT" 10)

  # Elapsed time bar + remaining time display
  ELAPSED_PCT=$((WINDOW_ELAPSED_MINS * 100 / 300))
  TIME_BAR=$(make_bar "$ELAPSED_PCT" 10)
  REMAINING_MINS=$((300 - WINDOW_ELAPSED_MINS))
  REMAINING_H=$((REMAINING_MINS / 60))
  REMAINING_M=$((REMAINING_MINS % 60))
  [ "$REMAINING_M" -gt 0 ] && REMAINING_STR="${REMAINING_H}h ${REMAINING_M}m" || REMAINING_STR="${REMAINING_H}h"

  if [ "$DIFF_ABS" -le 2 ]; then PCT_CLR='\033[32m'    # green — on pace (🔥)
  elif [ "$DIFF" -lt -2 ]; then PCT_CLR='\033[34m'   # blue — under budget (🧊)
  else PCT_CLR='\033[31m'; fi                         # red — over budget (🚨)
  RATE_SECTION="${PCT_CLR}${FIVE_H_INT}%\033[0m (${EMOJI} ${DIFF_SIGNED}%)  ${REMAINING_STR}  |  "
fi

SESSION_H=$((MINS / 60))
SESSION_M=$((MINS % 60))
[ "$SESSION_M" -gt 0 ] && SESSION_STR="${SESSION_H}h ${SESSION_M}m" || SESSION_STR="${SESSION_H}h"

echo -e "\033[1m${DIR}\033[0m  |  \033[36m${MODEL}\033[0m  |  ${RATE_SECTION}ctx ${PCT}%  |  ${SESSION_STR}"
