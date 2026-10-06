#!/bin/bash
#
# sync.sh — синхронизация конфигов между репо и ~/.
#
#   ./sync.sh              репо → ~/ : симлинки на файлы из home/, копия Karabiner, настройка iTerm2
#   ./sync.sh pull         ~/ → репо : копия Karabiner обратно в репо (запускать перед коммитом)
#   ./sync.sh --dry-run    показать план, ничего не менять (работает и с pull)
#   ./sync.sh --force      разрешить замену обычных файлов в ~/, которые отличаются от репо,
#                          и перезапись Karabiner при правках с обеих сторон
#
# Что делает ./sync.sh:
#   1. Берёт список файлов из git (git ls-files home), а не с диска — мусор вроде
#      .DS_Store и __pycache__ не попадает в ~/.
#   2. На каждый файл создаёт симлинк ~/<путь> → <репо>/home/<путь>.
#   3. Если в ~/ лежит обычный файл, который отличается от репо — НЕ трогает его,
#      печатает CONFLICT с diff. Заменить можно только с --force.
#   4. Заменённые файлы складывает в .backup/<дата>/, хранит последние 5 снимков.
#   5. Удаляет в корзину висячие симлинки, которые ведут в репо на уже удалённые файлы.
#   6. Karabiner не переживает симлинки — папка копируется. Перед копированием
#      сравнивается содержимое папок; если в приёмнике есть более новые или
#      лишние файлы — CONFLICT и пропуск.
#   7. iTerm2 умеет читать настройки из произвольной папки — прописываем путь к репо
#      через defaults write, симлинк не нужен.
#   8. BTT-пресет пропускается (импортируется вручную).
#
# Запускать только из основного чекаута, не из git worktree: симлинки должны
# вести туда, где репо живёт постоянно. Скрипт это проверяет сам.
#

set -eo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOME_DIR="$HOME"
BACKUP_ROOT="$REPO_DIR/.backup"
BACKUP_DIR="$BACKUP_ROOT/$(date +%Y-%m-%d_%H-%M-%S)"
BACKUPS_TO_KEEP=5

# Пути (относительно home/), которые не симлинкаются
SKIP_PREFIXES=(
    ".config/btt_preset.bttpreset"
    ".config/iterm2/"
    ".config/karabiner/"
)

# Каталоги в ~/, где ищем висячие симлинки, ведущие в репо
LINK_ROOTS=(
    ".config"
    ".claude"
    "Library/Application Support"
    "Library/Preferences"
)

KARABINER_REPO="$REPO_DIR/home/.config/karabiner"
KARABINER_HOME="$HOME_DIR/.config/karabiner"
RSYNC_OPTS=(-a --checksum --delete --exclude automatic_backups --exclude .DS_Store)

MODE="push"
DRY_RUN=0
FORCE=0
CONFLICTS=()

usage() {
    sed -n '2,/^$/p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

for arg in "$@"; do
    case "$arg" in
        pull)        MODE="pull" ;;
        --dry-run)   DRY_RUN=1 ;;
        --force)     FORCE=1 ;;
        -h|--help)   usage; exit 0 ;;
        *)           echo "Неизвестный аргумент: $arg" >&2; usage >&2; exit 1 ;;
    esac
done

# Выполнить команду, либо показать её в режиме --dry-run
run() {
    if (( DRY_RUN )); then
        echo "      [dry-run] $*"
    else
        "$@"
    fi
}

ensure_main_checkout() {
    local git_dir common_dir
    git_dir="$(git -C "$REPO_DIR" rev-parse --path-format=absolute --git-dir)"
    common_dir="$(git -C "$REPO_DIR" rev-parse --path-format=absolute --git-common-dir)"
    if [ "$git_dir" != "$common_dir" ]; then
        echo "Ошибка: скрипт запущен из git worktree:" >&2
        echo "  $REPO_DIR" >&2
        echo "Симлинки должны вести в основной чекаут. Запусти оттуда:" >&2
        echo "  $(dirname "$common_dir")/sync.sh" >&2
        exit 1
    fi
}

ensure_trash() {
    if ! command -v trash >/dev/null 2>&1; then
        echo "Ошибка: не найдена утилита trash (macOS 15+ или brew install trash)." >&2
        exit 1
    fi
}

should_skip() {
    local rel="$1" prefix
    for prefix in "${SKIP_PREFIXES[@]}"; do
        [[ "$rel" == "$prefix"* ]] && return 0
    done
    return 1
}

backup() {
    local path="$1" rel="$2" dest="$BACKUP_DIR/$rel"
    run mkdir -p "$(dirname "$dest")"
    run mv "$path" "$dest"
    echo "BACK  $rel -> .backup/$(basename "$BACKUP_DIR")/"
}

link_files() {
    local rel src dst
    while IFS= read -r -d '' rel; do
        rel="${rel#home/}"
        if should_skip "$rel"; then
            echo "SKIP  $rel"
            continue
        fi
        src="$REPO_DIR/home/$rel"
        dst="$HOME_DIR/$rel"

        if [ -L "$dst" ]; then
            if [ "$(readlink "$dst")" = "$src" ]; then
                echo "OK    $rel"
                continue
            fi
            backup "$dst" "$rel"
        elif [ -e "$dst" ]; then
            if cmp -s "$dst" "$src"; then
                backup "$dst" "$rel"
            elif (( FORCE )); then
                echo "FORCE $rel — обычный файл в ~/ отличается от репо, заменяю"
                backup "$dst" "$rel"
            else
                echo "CONFLICT $rel — в ~/ обычный файл, отличается от репо. Пропущен (--force чтобы заменить)"
                diff -u "$src" "$dst" | head -40 | sed 's/^/      /' || true
                CONFLICTS+=("$rel")
                continue
            fi
        fi

        run mkdir -p "$(dirname "$dst")"
        run ln -s "$src" "$dst"
        echo "LINK  $rel"
    done < <(git -C "$REPO_DIR" ls-files -z home)
}

clean_dangling_links() {
    local root link target
    for root in "${LINK_ROOTS[@]}"; do
        [ -d "$HOME_DIR/$root" ] || continue
        while IFS= read -r -d '' link; do
            [ -e "$link" ] && continue
            target="$(readlink "$link")"
            case "$target" in
                "$REPO_DIR"/home/*)
                    run trash "$link"
                    echo "DEAD  ${link#$HOME_DIR/} -> ${target#$REPO_DIR/} (висячая ссылка, в корзину)"
                    ;;
            esac
        done < <(find "$HOME_DIR/$root" -maxdepth 8 -type l \
                    -not -path '*/worktrees/*' -not -path '*/node_modules/*' -print0 2>/dev/null)
    done
}

setup_iterm() {
    run defaults write com.googlecode.iterm2 PrefsCustomFolder -string "$REPO_DIR/home/.config/iterm2"
    run defaults write com.googlecode.iterm2 LoadPrefsFromCustomFolder -bool true
    echo "ITERM конфиг -> $REPO_DIR/home/.config/iterm2/"
}

# sync_karabiner push|pull
sync_karabiner() {
    local direction="$1" src dst label line f
    local changes=() deletions=() conflicts=()

    if [ "$direction" = "push" ]; then
        src="$KARABINER_REPO"; dst="$KARABINER_HOME"; label="repo -> ~/"
    else
        src="$KARABINER_HOME"; dst="$KARABINER_REPO"; label="~/ -> repo"
    fi
    if [ ! -d "$src" ]; then
        echo "KARAB нет $src — пропуск"
        return
    fi
    [ -d "$dst" ] || run mkdir -p "$dst"

    while IFS= read -r line; do
        [ -n "$line" ] || continue
        case "$line" in
            "deleting "*) deletions+=("${line#deleting }") ;;
            */)           ;;
            *)            changes+=("$line") ;;
        esac
    done < <(rsync -an --out-format='%n' "${RSYNC_OPTS[@]}" "$src/" "$dst/" 2>/dev/null || true)

    if (( ${#changes[@]} == 0 && ${#deletions[@]} == 0 )); then
        echo "OK    karabiner ($label, без изменений)"
        return
    fi

    for f in ${changes[@]+"${changes[@]}"}; do
        if [ -e "$dst/$f" ] && [ "$dst/$f" -nt "$src/$f" ]; then
            conflicts+=("$f")
        fi
    done

    if (( ! FORCE )) && (( ${#conflicts[@]} + ${#deletions[@]} > 0 )); then
        echo "CONFLICT karabiner ($label) — пропущено. Разберись руками или --force:"
        for f in ${conflicts[@]+"${conflicts[@]}"}; do
            echo "      $f: в приёмнике новее, чем в источнике"
        done
        for f in ${deletions[@]+"${deletions[@]}"}; do
            echo "      $f: есть только в приёмнике, копирование его удалит"
        done
        CONFLICTS+=("karabiner")
        return
    fi

    run rsync "${RSYNC_OPTS[@]}" "$src/" "$dst/"
    echo "COPY  karabiner ($label): ${changes[*]-}${deletions[*]+ удалено: ${deletions[*]}}"
}

rotate_backups() {
    [ -d "$BACKUP_ROOT" ] || return 0
    local total excess name
    total=$(/bin/ls -1 "$BACKUP_ROOT" | wc -l | tr -d ' ')
    excess=$(( total - BACKUPS_TO_KEEP ))
    (( excess > 0 )) || return 0
    while IFS= read -r name; do
        run trash "$BACKUP_ROOT/$name"
        echo "PRUNE .backup/$name (старый снимок, в корзину)"
    done < <(/bin/ls -1 "$BACKUP_ROOT" | sort | head -n "$excess")
}

report() {
    echo ""
    if (( DRY_RUN )); then
        echo "Dry-run: ничего не изменено."
    else
        echo "Готово."
    fi
    if [ -d "$BACKUP_DIR" ]; then
        echo "Бэкапы: $BACKUP_DIR"
    fi
    if (( ${#CONFLICTS[@]} > 0 )); then
        echo ""
        echo "Конфликты (пропущены): ${CONFLICTS[*]}"
        echo "Посмотри diff выше. Чтобы взять версию из репо: ./sync.sh --force"
        exit 2
    fi
}

ensure_main_checkout
ensure_trash

echo "Репо: $REPO_DIR/home"
echo "Цель: $HOME_DIR"
(( DRY_RUN )) && echo "Режим: dry-run"
echo ""

case "$MODE" in
    push)
        link_files
        clean_dangling_links
        setup_iterm
        sync_karabiner push
        rotate_backups
        ;;
    pull)
        sync_karabiner pull
        ;;
esac

report
