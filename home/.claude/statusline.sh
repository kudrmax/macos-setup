#!/bin/bash
input=$(cat)

MODEL=$(echo "$input" | jq -r '.model.display_name // "?"')
PCT=$(echo "$input" | jq -r '.context_window.used_percentage // 0' | cut -d. -f1)
DURATION_MS=$(echo "$input" | jq -r '.cost.total_duration_ms // 0')
FIVE_H=$(echo "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty')
FIVE_H_RESETS_AT=$(echo "$input" | jq -r '.rate_limits.five_hour.resets_at // empty')
DIR=$(echo "$input" | jq -r '.workspace.current_dir // "?"')
DIR="${DIR##*/}"

RESET='\033[0m'
BOLD='\033[1m'

BRIGHT="100;120;165"
DARK="22;26;38"
S5="56;52;52"
S6="36;34;34"

lerp() {
  awk -v f="$1" -v t="$2" -v s="$3" -v i="$4" 'BEGIN {
    split(f,a,";"); split(t,b,";")
    for(j=1;j<=3;j++) c[j]=int(a[j]+(b[j]-a[j])*i/s)
    print c[1]";"c[2]";"c[3]
  }'
}

text_color() {
  echo "$1" | awk -F';' '{lum=$1*0.299+$2*0.587+$3*0.114; print (lum>140) ? "\033[38;2;30;30;30m" : "\033[97m"}'
}

arr()     { echo -en "\033[38;2;${1}m\033[48;2;${2}m\xee\x82\xb4"; }
end_cap() { echo -e "${RESET}\033[38;2;${1}m\xee\x82\xb4${RESET}"; }

row_start() {
  local bg="$1" text="$2" bold="${3:-}"
  local fg
  fg=$(text_color "$bg")
  echo -en "\033[38;2;${bg}m\xee\x82\xb6\033[48;2;${bg}m${fg}${bold} ${text}\033[48;2;${bg}m${fg} "
}

seg() {
  local prev_bg="$1" bg="$2" text="$3"
  local fg
  fg=$(text_color "$bg")
  arr "$prev_bg" "$bg"
  echo -en "\033[48;2;${bg}m${fg} ${text}\033[48;2;${bg}m${fg} "
}

S2=$(lerp "$BRIGHT" "$DARK" 4 1)
S3=$(lerp "$BRIGHT" "$DARK" 4 2)
S4=$(lerp "$BRIGHT" "$DARK" 4 3)

MINS=$((DURATION_MS / 60000))
SESSION_H=$((MINS / 60))
SESSION_M=$((MINS % 60))
[ "$SESSION_M" -gt 0 ] && SESSION_STR="${SESSION_H}h ${SESSION_M}m" || SESSION_STR="${SESSION_H}h"

# Line 1: DIR | MODEL [| rate | remaining]
row_start "$BRIGHT" "$DIR" "$BOLD"
seg "$BRIGHT" "$S2" "$MODEL"

if [ -n "$FIVE_H" ]; then
  FIVE_H_INT=${FIVE_H%%.*}

  WINDOW_ELAPSED_MINS=0
  if [ -n "$FIVE_H_RESETS_AT" ]; then
    NOW=$(date +%s)
    WINDOW_START=$((FIVE_H_RESETS_AT - 18000))
    WINDOW_ELAPSED_SECS=$((NOW - WINDOW_START))
    WINDOW_ELAPSED_MINS=$((WINDOW_ELAPSED_SECS / 60))
    [ "$WINDOW_ELAPSED_MINS" -lt 0 ] && WINDOW_ELAPSED_MINS=0
    [ "$WINDOW_ELAPSED_MINS" -gt 300 ] && WINDOW_ELAPSED_MINS=300
  fi

  EXPECTED_PCT=$((WINDOW_ELAPSED_MINS * 100 / 300))
  DIFF=$((FIVE_H_INT - EXPECTED_PCT))
  DIFF_ABS=${DIFF#-}
  [ "$DIFF" -gt 0 ] && DIFF_SIGNED="+${DIFF}" || DIFF_SIGNED="${DIFF}"
  if [ "$DIFF_ABS" -le 2 ]; then EMOJI="🔥"
  elif [ "$DIFF" -lt -2 ]; then EMOJI="🧊"
  else EMOJI="🚨"; fi

  REMAINING_MINS=$((300 - WINDOW_ELAPSED_MINS))
  REMAINING_H=$((REMAINING_MINS / 60))
  REMAINING_M=$((REMAINING_MINS % 60))
  [ "$REMAINING_M" -gt 0 ] && REMAINING_STR="${REMAINING_H}h ${REMAINING_M}m" || REMAINING_STR="${REMAINING_H}h"

  seg "$S2" "$S3" "${EMOJI} ${FIVE_H_INT}% (${DIFF_SIGNED}%)"
  seg "$S3" "$S4" "$REMAINING_STR"
  end_cap "$S4"
else
  end_cap "$S2"
fi

# Line 2: plain text
echo -e "ctx ${PCT}%   ${SESSION_STR}"
