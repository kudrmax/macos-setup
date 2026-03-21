#!/bin/bash
#
# copy.sh — копирует конфиги, которые нельзя симлинкать, из ~/ в репо.
#
# Некоторые приложения (например, Karabiner) ломают симлинки при записи,
# поэтому для них используется ручное копирование.
#

set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

# Karabiner (всё кроме automatic_backups)
rsync -aL --delete \
    --exclude 'automatic_backups' \
    ~/.config/karabiner/ \
    "$REPO_DIR/home/.config/karabiner/"
echo "OK  karabiner"
