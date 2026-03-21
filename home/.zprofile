# brew — пакетный менеджер, задаёт PATH/MANPATH/HOMEBREW_PREFIX для всех brew-пакетов
eval "$(/opt/homebrew/bin/brew shellenv)"

# Avito AI — автодополнение для внутренних CLI-утилит
export FPATH=$HOME/.config/ai/zsh:$FPATH

# Avito внутренний brew — зеркала репозиториев вместо публичных GitHub
export HOMEBREW_CORE_GIT_REMOTE="https://stash.msk.avito.ru/scm/mrr/brew-core.git"
export HOMEBREW_BOTTLE_DOMAIN="https://brew-proxy.k.avito.ru/bottles"
export HOMEBREW_BREW_GIT_REMOTE="https://stash.msk.avito.ru/scm/mrr/brew.git"

# Obsidian — CLI-доступ к приложению заметок
export PATH="$PATH:/Applications/Obsidian.app/Contents/MacOS"
