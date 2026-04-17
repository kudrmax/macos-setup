# p10k instant prompt — должен быть в самом начале файла
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

# oh-my-zsh — фреймворк для плагинов и настроек zsh
export ZSH="$HOME/.oh-my-zsh"
plugins=(git command-not-found)
source $ZSH/oh-my-zsh.sh

# Алиасы
alias zshconfig="vim ~/.zshrc"
alias c="clear"
alias с="clear"

# Современные замены стандартных утилит
alias cat="bat"
alias ls="eza --icons"
alias ll="eza -la --icons --git"
alias tree="eza --tree --icons"
alias rm="trash"

# brew — всегда без корпоративного прокси
brew() {
  HOMEBREW_BOTTLE_DOMAIN="" HOMEBREW_CORE_GIT_REMOTE="" HOMEBREW_BREW_GIT_REMOTE="" command brew "$@"
}

# avito — запуск без внешнего VPN
avito() {
  http_proxy="" https_proxy="" all_proxy="" command avito "$@"
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

# zoxide — умная навигация по директориям (замена z)
eval "$(zoxide init zsh)"
alias cd="z"

# fzf — нечёткий поиск (Ctrl+T файлы, Cmd+Shift+R история)
eval "$(fzf --zsh)"
bindkey -r '^R'  # убираем Ctrl+R у fzf, отдаём atuin
bindkey '\e[82;9u' fzf-history-widget  # Cmd+Shift+R → fzf история (iTerm2 CSI u)

# atuin — улучшенная история команд (Ctrl+R)
eval "$(atuin init zsh)"

# libpq — утилиты PostgreSQL (psql, pg_dump) без полной установки сервера
export PATH="/opt/homebrew/opt/libpq/bin:$PATH"
# llvm — clang/clang++ и утилиты (для сборки C/C++ зависимостей)
export PATH="/opt/homebrew/opt/llvm/bin:$PATH"

# nvm — ленивая загрузка (NVM_DIR задан в .zshenv)
for _nvm_cmd in nvm node npm npx; do
  eval "
    ${_nvm_cmd}() {
      unset -f nvm node npm npx
      [ -s '/opt/homebrew/opt/nvm/nvm.sh' ] && . '/opt/homebrew/opt/nvm/nvm.sh'
      [ -s '/opt/homebrew/opt/nvm/etc/bash_completion.d/nvm' ] && . '/opt/homebrew/opt/nvm/etc/bash_completion.d/nvm'
      ${_nvm_cmd} \"\$@\"
    }
  "
done
unset _nvm_cmd

# Go — рабочая директория и бинарники (go install кладёт сюда)
export GOPATH="$HOME/go"
export PATH="$PATH:$GOPATH/bin"

# LM Studio — локальный запуск LLM-моделей
export PATH="$PATH:$HOME/.lmstudio/bin"

# Android — Gradle кэш в Shared (для beduinv2), JDK 17
export GRADLE_USER_HOME=/Users/Shared/gradle
export JAVA_HOME=/Library/Java/JavaVirtualMachines/openjdk-17.jdk/Contents/Home

# kanban-md — Kanban в markdown
alias k="kanban-md"

# Anything to Anki — две физически изолированные рабочие копии.
# anki-dev — перейти в dev-копию (для разработки).
# anki-run — перейти в prod-копию и запустить (реальное использование).
anki-dev() {
  cd /Users/mdmkudryashov/PycharmProjects/anything-to-anki
}
anki-run() {
  cd /Users/mdmkudryashov/Applications/anything-to-anki-prod && make up
}

# vpn-check — проверка, что Hiddify поднят и трафик ходит через прокси
vpn-check() {
  local proxy="http://127.0.0.1:12334"
  if ! curl -s -m 3 -o /dev/null -x "$proxy" https://www.google.com; then
    echo "FAIL: Hiddify недоступен на 127.0.0.1:12334 (не запущен или порт другой)"
    return 1
  fi
  local ip
  ip=$(curl -s -m 5 -x "$proxy" https://api.ipify.org)
  echo "OK: VPN работает, внешний IP через прокси: ${ip:-unknown}"
}

# vpn-on — активировать Hiddify-прокси в текущем терминале (скопируй в новый шелл при необходимости):
#   export http_proxy="http://127.0.0.1:12334"
#   export https_proxy="http://127.0.0.1:12334"
#   export all_proxy="socks5://127.0.0.1:12334"
vpn-on() {
  export http_proxy="http://127.0.0.1:12334"
  export https_proxy="http://127.0.0.1:12334"
  export all_proxy="socks5://127.0.0.1:12334"
  echo "VPN-прокси активирован в этом шелле (http/https/all → 127.0.0.1:12334)"
}

# vpn-off — снять прокси в текущем терминале
vpn-off() {
  unset http_proxy https_proxy all_proxy
  echo "VPN-прокси снят"
}

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

# clb() — cl + bypass permissions
clb() {
  cl --dangerously-skip-permissions "$@"
}

test -e "${HOME}/.iterm2_shell_integration.zsh" && source "${HOME}/.iterm2_shell_integration.zsh" || true

