# p10k instant prompt — должен быть в самом начале файла
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

# oh-my-zsh — фреймворк для плагинов и настроек zsh
export ZSH="$HOME/.oh-my-zsh"
plugins=(git z)
source $ZSH/oh-my-zsh.sh

# Алиасы
alias zshconfig="vim ~/.zshrc"
alias c="clear"
alias с="clear"

# nbrew — brew без корпоративного прокси (для работы вне VPN)
nbrew() {
  HOMEBREW_BOTTLE_DOMAIN="" HOMEBREW_CORE_GIT_REMOTE="" HOMEBREW_BREW_GIT_REMOTE="" brew "$@"
}

# brew prefix — кешируем, чтобы не вызывать subprocess на каждый source
BREW_PREFIX="$(brew --prefix)"

# p10k — тема для prompt, настройки в ~/.p10k.zsh
source $BREW_PREFIX/share/powerlevel10k/powerlevel10k.zsh-theme
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

# Плагины через brew (не через oh-my-zsh, т.к. brew обновляет их автоматически)
source $BREW_PREFIX/share/zsh-autosuggestions/zsh-autosuggestions.zsh
source $BREW_PREFIX/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
source $BREW_PREFIX/share/zsh-history-substring-search/zsh-history-substring-search.zsh
source $BREW_PREFIX/share/zsh-you-should-use/you-should-use.plugin.zsh

# fzf — нечёткий поиск (Ctrl+R история, Ctrl+T файлы)
eval "$(fzf --zsh)"

# libpq — утилиты PostgreSQL (psql, pg_dump) без полной установки сервера
export PATH="/opt/homebrew/opt/libpq/bin:$PATH"
# llvm — clang/clang++ и утилиты (для сборки C/C++ зависимостей)
export PATH="/opt/homebrew/opt/llvm/bin:$PATH"

# nvm — ленивая загрузка (грузится при первом вызове nvm/node/npm/npx)
export NVM_DIR="$HOME/.nvm"
_nvm_lazy_load() {
  unset -f nvm node npm npx
  [ -s "/opt/homebrew/opt/nvm/nvm.sh" ] && \. "/opt/homebrew/opt/nvm/nvm.sh"
  [ -s "/opt/homebrew/opt/nvm/etc/bash_completion.d/nvm" ] && \. "/opt/homebrew/opt/nvm/etc/bash_completion.d/nvm"
}
for cmd in nvm node npm npx; do
  eval "${cmd}() { _nvm_lazy_load; ${cmd} \"\$@\" }"
done

# Go — рабочая директория и бинарники (go install кладёт сюда)
export GOPATH="$HOME/go"
export PATH="$PATH:$GOPATH/bin"

# LM Studio — локальный запуск LLM-моделей
export PATH="$PATH:/Users/mdmkudryashov/.lmstudio/bin"

# Android — Gradle кэш в Shared (для beduinv2), JDK 17, Node для сборки
export GRADLE_USER_HOME=/Users/Shared/gradle
export JAVA_HOME=/Library/Java/JavaVirtualMachines/openjdk-17.jdk/Contents/Home
export PATH="/opt/homebrew/opt/node@22/bin:$PATH"

# life() — запуск Claude в проекте life-analytics через прокси
life() {
  clear
  cd ~/PycharmProjects/life-analytics
  export http_proxy="http://127.0.0.1:12334"
  export https_proxy="http://127.0.0.1:12334"
  export all_proxy="socks5://127.0.0.1:12334"
  claude "$@"
}

# cl() — запуск Claude через прокси из текущей директории
cl() {
  clear
  export http_proxy="http://127.0.0.1:12334"
  export https_proxy="http://127.0.0.1:12334"
  export all_proxy="socks5://127.0.0.1:12334"
  claude "$@"
}

test -e "${HOME}/.iterm2_shell_integration.zsh" && source "${HOME}/.iterm2_shell_integration.zsh" || true

