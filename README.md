# macOS setup

Конфиги и инструкции для настройки macOS с нуля. Конфиги хранятся в `home/` и симлинкаются в `~/` скриптом `sync.sh`.

## Быстрый старт

```bash
# 1. Установить Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Склонировать репо
git clone https://github.com/kudrmax/macos-setup ~/macos-setup

# 3. Установить зависимости (см. разделы ниже)

# 4. Создать симлинки
cd ~/macos-setup
./sync.sh
```

> [!WARNING]
> `home/.gitconfig` содержит мой email. После `sync.sh` проверьте `git config user.email`.

## Terminal

### Oh-My-Zsh + Powerlevel10k

```bash
# Oh-My-Zsh
sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"

# Тема
brew install powerlevel10k

# Плагины
brew install zsh-autosuggestions
brew install zsh-syntax-highlighting
brew install zsh-history-substring-search
brew install zsh-you-should-use

# Инструменты
brew install fzf
brew install micro
```

Шрифты для p10k (если не установились автоматически): [ссылка](https://github.com/romkatv/powerlevel10k?tab=readme-ov-file#manual-font-installation)

Перенастроить prompt (если нужно):
```bash
p10k configure
```

### iTerm2

```bash
brew install --cask iterm2
```

Импорт настроек: Settings → General → Settings → Import All Settings and Data... → `~/macos-setup/home/.config/iTerm2 State.itermexport`

### Lazygit + Lazydocker

```bash
brew install lazygit
brew install git-delta  # красивый diff (side-by-side)
brew install lazydocker
```

### Языки и рантаймы

```bash
# Go
brew install go

# Node.js (через nvm)
brew install nvm

# Python — используем venv, не conda

# PostgreSQL CLI (psql, pg_dump без сервера)
brew install libpq

# LLVM
brew install llvm
```

## Приложения

```bash
brew install --cask google-chrome
brew install --cask telegram
brew install --cask iina
brew install --cask todoist
brew install --cask obsidian
brew install --cask morgen
brew install --cask yandex-music
```

## Утилиты

```bash
brew install --cask bitwarden
brew install --cask appcleaner
brew install --cask bettertouchtool
brew install --cask karabiner-elements
brew install --cask sublime-text
```

- [Xnip](https://xnipapp.com/) — скриншоты
- [Maccy](https://maccy.app/) — менеджер буфера обмена
- [OwlOCR](https://www.owlocr.com/) — OCR

### AI

```bash
brew install --cask lm-studio  # локальный запуск LLM
```

Claude Code — устанавливается отдельно. Конфиги в `home/.claude/` (CLAUDE.md, settings.json, skills).

### BTT (Better Touch Tool)

Импортировать настройки:
1. Presets → Import presets → `~/macos-setup/home/.config/btt_preset.bttpreset`
2. Preset (в левом верхнем углу) → удалить default preset
3. Fix 4 Finger Swipe Down: 4 Finger Swipe Down → Application Switcher → Use Gesture Mode

### Karabiner Elements

```bash
brew install --cask karabiner-elements
```

Конфиг симлинкается автоматически через `sync.sh`. Если проблемы с `karabiner_grabber` — перезагрузить компьютер.

### Chrome расширения

- [Bitwarden](https://chromewebstore.google.com/detail/bitwarden-password-manage/nngceckbapebfimnlniiiahkandclblb)
- [Video Speed Controller](https://chromewebstore.google.com/detail/video-speed-controller/nffaoalbilbmmfgbnbgppjihopabppdk)
- [AdBlock](https://chromewebstore.google.com/detail/adblock-%E2%80%94-block-ads-acros/gighmmpiobklfepjocnamgkkbiglidom)
- [SponsorBlock](https://chromewebstore.google.com/detail/sponsorblock-for-youtube/mnjggcdmjocbbbhaepdhchncahnbgone)

## Структура репо

```
~/macos-setup/
├── sync.sh                 ← создаёт симлинки из home/ в ~/
├── README.md
├── .gitignore
└── home/                   ← зеркало ~/, конфиги хранятся здесь
    ├── .zshrc
    ├── .zprofile
    ├── .p10k.zsh
    ├── .gitconfig
    ├── .claude/            ← Claude Code (инструкции, настройки, скиллы)
    ├── .config/
    │   ├── karabiner/      ← конфиг + правила
    │   ├── mpv/            ← скрипты и конфиги для MPV
    │   ├── btt_preset.bttpreset  ← ручной импорт
    │   └── iTerm2 State.itermexport  ← ручной импорт
    └── Library/Application Support/
        ├── lazygit/config.yml
        ├── lazydocker/config.yml
        ├── Code/User/settings.json  ← VS Code
        └── com.colliderli.iina/     ← IINA горячие клавиши
```

## Как это работает

`sync.sh` проходит по всем файлам в `home/` и создаёт симлинки:
- `~/.zshrc` → `~/macos-setup/home/.zshrc`
- `~/.config/karabiner/karabiner.json` → `~/macos-setup/home/.config/karabiner/karabiner.json`
- и т.д.

Если файл уже существует — бэкапится в `.backup/`. Файлы BTT и iTerm2 пропускаются (нужен ручной импорт).

После этого любые изменения конфигов сразу видны в `git status`.
