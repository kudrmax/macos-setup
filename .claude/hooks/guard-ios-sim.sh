#!/bin/bash
# Blocks simulator runtimes and Xcode versions, and any simulator beyond the four working ones (iOS 26.3, Xcode 26.3).
input=$(cat)
cmd=$(jq -r '.tool_input.command // ""' <<<"$input")
create='simctl[[:space:]]+(create|clone)'
install='simctl[[:space:]]+runtime[[:space:]]+(add|import)|xcodebuild.*-(downloadPlatform|downloadAllPlatforms|importPlatform)|xcodes[[:space:]]+(install|runtimes[[:space:]]+install)|mas[[:space:]]+install[[:space:]]+497799835'
limit=4

if grep -qE "$install" <<<"$cmd"; then
	echo "Новые рантаймы iOS и версии Xcode ставить запрещено: на ноуте один Xcode 26.3 (/Applications/Xcode-26.3.0.app) и одна iOS 26.3. Если без них задачу не сделать, остановись и спроси Макса." >&2
	exit 2
fi

if grep -qE "$create" <<<"$cmd"; then
	count=$(xcrun simctl list devices -j 2>/dev/null | jq '[.devices[][]] | length')
	if [ "${count:-0}" -ge "$limit" ]; then
		echo "Новые симуляторы не создавать: рабочих iPhone 16 Pro ровно $limit. Возьми свободный: ~/.claude/bin/ios-sim take <кто>; все заняты — ~/.claude/bin/ios-sim wait <кто>. Если без нового симулятора задачу не сделать, остановись и спроси Макса." >&2
		exit 2
	fi
fi

# Any call naming a held simulator keeps its lock alive (ios-sim: a lock untouched for an hour counts as abandoned).
for udid in $(grep -oE '[0-9A-F]{8}-([0-9A-F]{4}-){3}[0-9A-F]{12}' <<<"$input" | sort -u); do
	[ -d "$HOME/.claude/sim-locks/$udid" ] && touch "$HOME/.claude/sim-locks/$udid/beat"
done
exit 0
