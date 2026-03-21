#!/bin/bash
#
# install.sh — привязывает конфиги из этого репо к домашней директории через симлинки.
#
# Что делает:
#   1. Проходит по всем файлам в macos-setup/home/
#   2. Для каждого файла создаёт симлинк: ~/путь -> macos-setup/home/путь
#      Например: ~/.zshrc -> ~/macos-setup/home/.zshrc
#   3. Если в ~/ уже есть такой файл — сначала бэкапит его в macos-setup/.backup/
#   4. Файлы из SKIP_PATTERNS (BTT) пропускает — их нужно импортировать вручную
#   5. Настраивает iTerm2 на хранение конфига в ~/.config/iterm2/
#
# После этого любые изменения конфигов сразу видны в git status репо.
#
# Использование:
#   ./install.sh
#

set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
HOME_DIR="$HOME"
BACKUP_DIR="$REPO_DIR/.backup/$(date +%Y-%m-%d_%H-%M-%S)"

# Файлы, которые нельзя симлинкать (нужен ручной импорт)
SKIP_PATTERNS=(
    "btt_preset.bttpreset"
    ".config/iterm2/"
)

should_skip() {
    local file="$1"
    for pattern in "${SKIP_PATTERNS[@]}"; do
        if [[ "$file" == *"$pattern"* ]]; then
            return 0
        fi
    done
    return 1
}

echo "Репо: $REPO_DIR/home"
echo "Цель: $HOME_DIR"
echo ""

# Находим все файлы в home/
find "$REPO_DIR/home" -type f | while read -r src; do
    # Относительный путь от home/
    rel="${src#$REPO_DIR/home/}"

    # Пропускаем файлы, которые нельзя симлинкать
    if should_skip "$rel"; then
        echo "SKIP  $rel (ручной импорт)"
        continue
    fi

    dst="$HOME_DIR/$rel"
    dst_dir="$(dirname "$dst")"

    # Если уже симлинк на правильный файл — ничего не делаем
    if [ -L "$dst" ] && [ "$(readlink "$dst")" = "$src" ]; then
        echo "OK    $rel"
        continue
    fi

    # Если файл существует (не симлинк) — бэкапим
    if [ -e "$dst" ] || [ -L "$dst" ]; then
        backup_path="$BACKUP_DIR/$rel"
        mkdir -p "$(dirname "$backup_path")"
        mv "$dst" "$backup_path"
        echo "BACK  $rel -> .backup/"
    fi

    # Создаём директорию и симлинк
    mkdir -p "$dst_dir"
    ln -s "$src" "$dst"
    echo "LINK  $rel"
done

# iTerm2: симлинк директории + настройка custom folder
ITERM2_SRC="$REPO_DIR/home/.config/iterm2"
ITERM2_DST="$HOME_DIR/.config/iterm2"

if [ -L "$ITERM2_DST" ] && [ "$(readlink "$ITERM2_DST")" = "$ITERM2_SRC" ]; then
    echo "OK    .config/iterm2/ (dir symlink)"
else
    if [ -e "$ITERM2_DST" ] || [ -L "$ITERM2_DST" ]; then
        backup_path="$BACKUP_DIR/.config/iterm2"
        mkdir -p "$(dirname "$backup_path")"
        mv "$ITERM2_DST" "$backup_path"
        echo "BACK  .config/iterm2/ -> .backup/"
    fi
    mkdir -p "$(dirname "$ITERM2_DST")"
    ln -s "$ITERM2_SRC" "$ITERM2_DST"
    echo "LINK  .config/iterm2/ (dir symlink)"
fi

defaults write com.googlecode.iterm2 PrefsCustomFolder -string "$HOME/.config/iterm2"
defaults write com.googlecode.iterm2 LoadPrefsFromCustomFolder -bool true
echo "iTerm2: конфиг -> ~/.config/iterm2/"

echo ""
echo "Готово."
if [ -d "$BACKUP_DIR" ]; then
    echo "Бэкапы: $BACKUP_DIR"
fi
