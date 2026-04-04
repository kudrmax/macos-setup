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

S2=$(lerp "$BRIGHT" "$DARK" 4 1)
S3=$(lerp "$BRIGHT" "$DARK" 4 2)
S4=$(lerp "$BRIGHT" "$DARK" 4 3)

MINS=$((DURATION_MS / 60000))
SESSION_H=$((MINS / 60))
SESSION_M=$((MINS % 60))
[ "$SESSION_M" -gt 0 ] && SESSION_STR="${SESSION_H}h ${SESSION_M}m" || SESSION_STR="${SESSION_H}h"

# Segment 1: DIR
fg=$(text_color "$BRIGHT")
echo -en "\033[38;2;${BRIGHT}m\xee\x82\xb6\033[48;2;${BRIGHT}m${fg} ${BOLD}${DIR}\033[48;2;${BRIGHT}m${fg} "

# Segment 2: MODEL
fg=$(text_color "$S2")
arr "$BRIGHT" "$S2"
echo -en "\033[48;2;${S2}m${fg} ${MODEL}\033[48;2;${S2}m${fg} "

PREV="$S2"

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

  # Segment 3: rate
  fg=$(text_color "$S3")
  arr "$PREV" "$S3"
  echo -en "\033[48;2;${S3}m${fg} ${EMOJI} ${FIVE_H_INT}% (${DIFF_SIGNED}%)\033[48;2;${S3}m${fg} "

  # Segment 4: remaining
  fg=$(text_color "$S4")
  arr "$S3" "$S4"
  echo -en "\033[48;2;${S4}m${fg} ${REMAINING_STR}\033[48;2;${S4}m${fg} "

  PREV="$S4"
fi

# Segment 5: ctx
fg=$(text_color "$S5")
arr "$PREV" "$S5"
echo -en "\033[48;2;${S5}m${fg} ctx ${PCT}%\033[48;2;${S5}m${fg} "

# Segment 6: session
fg=$(text_color "$S6")
arr "$S5" "$S6"
echo -en "\033[48;2;${S6}m${fg} ${SESSION_STR}\033[48;2;${S6}m${fg} "

end_cap "$S6"
