#!/bin/bash
#
# sync.sh — привязывает конфиги из этого репо к домашней директории через симлинки.
#
# Что делает:
#   1. Проходит по всем файлам в macos-setup/home/
#   2. Для каждого файла создаёт симлинк: ~/путь -> macos-setup/home/путь
#      Например: ~/.zshrc -> ~/macos-setup/home/.zshrc
#   3. Если в ~/ уже есть такой файл — сначала бэкапит его в macos-setup/.backup/
#   4. Файлы из SKIP_PATTERNS пропускает — их нужно импортировать вручную
#   5. iTerm2: указывает PrefsCustomFolder напрямую на репо (симлинк не нужен)
#   6. Karabiner: копирует из репо в ~/ (симлинки ломает). Если ~/новее — предупреждает
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

# Файлы, которые не симлинкаются (обрабатываются отдельно или вручную)
SKIP_PATTERNS=(
    "btt_preset.bttpreset"
    ".config/iterm2/"
    ".config/karabiner/"
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
        echo "SKIP  $rel"
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

# iTerm2: нативно поддерживает PrefsCustomFolder — сам читает/пишет конфиг
# из указанной директории. Указываем напрямую на репо, симлинк не нужен.
defaults write com.googlecode.iterm2 PrefsCustomFolder -string "$REPO_DIR/home/.config/iterm2"
defaults write com.googlecode.iterm2 LoadPrefsFromCustomFolder -bool true
echo "iTerm2: конфиг -> $REPO_DIR/home/.config/iterm2/"

# Karabiner: не поддерживает симлинки — копируем из репо в ~/
KARABINER_SRC="$REPO_DIR/home/.config/karabiner"
KARABINER_DST="$HOME_DIR/.config/karabiner"
if [ -d "$KARABINER_SRC" ]; then
    if [ -d "$KARABINER_DST" ] && [ "$KARABINER_DST/karabiner.json" -nt "$KARABINER_SRC/karabiner.json" ]; then
        KARABINER_WARN="⚠️  karabiner: ~/настройки новее репо. Сначала запусти ./copy.sh, затем повтори ./sync.sh"
    else
        mkdir -p "$KARABINER_DST"
        rsync -a --exclude 'automatic_backups' \
            "$KARABINER_SRC/" "$KARABINER_DST/"
        echo "COPY  karabiner (repo -> ~/)"
    fi
fi

echo ""
echo "Готово."
if [ -d "$BACKUP_DIR" ]; then
    echo "Бэкапы: $BACKUP_DIR"
fi
if [ -n "$KARABINER_WARN" ]; then
    echo ""
    echo "$KARABINER_WARN"
fi
