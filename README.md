# macOS setup

Конфиги и инструкции для настройки macOS с нуля. Конфиги хранятся в `home/` и симлинкаются в `~/` скриптом `sync.sh`.

## Быстрый старт

```bash
# 1. Установить Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Склонировать репо
git clone https://github.com/kudrmax/macos-setup ~/macos-setup

# 3. Oh-My-Zsh
sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"

# 4. Установить все зависимости
cd ~/macos-setup
brew bundle

# 5. Создать симлинки
./sync.sh
```

> [!WARNING]
> `home/.gitconfig` содержит мой email. После `sync.sh` проверьте `git config user.email`.

## Ручная настройка после установки

### Шрифты Powerlevel10k

Если не установились автоматически: [ссылка](https://github.com/romkatv/powerlevel10k?tab=readme-ov-file#manual-font-installation)

Перенастроить prompt:
```bash
p10k configure
```

### iTerm2

Импорт настроек: Settings → General → Settings → Import All Settings and Data... → `~/macos-setup/home/.config/iTerm2 State.itermexport`

### BTT (Better Touch Tool)

1. Presets → Import presets → `~/macos-setup/home/.config/btt_preset.bttpreset`
2. Preset (в левом верхнем углу) → удалить default preset
3. Fix 4 Finger Swipe Down: 4 Finger Swipe Down → Application Switcher → Use Gesture Mode

### Karabiner Elements

Конфиг копируется автоматически через `sync.sh`. Если проблемы с `karabiner_grabber` — перезагрузить компьютер.

### Автообновление Homebrew

Устанавливает launchd-агент, который раз в сутки обновляет все формулы и cask-приложения в фоне:

```bash
brew tap domt4/autoupdate
brew autoupdate start 86400 --upgrade --cleanup --leaves-only --ac-only
```

Логи: `~/Library/Logs/com.github.domt4.homebrew-autoupdate/com.github.domt4.homebrew-autoupdate.out`

### Bruno

```bash
git clone git@github.com:kudrmax/bruno-collections.git ~/bruno
```

Коллекции запросов хранятся в отдельном приватном репо. После клонирования Bruno подхватит их автоматически (путь прописан в `preferences.json`).

### VPN

- [Hiddify](https://github.com/hiddify/hiddify-app/releases/latest) — клиент для прокси-протоколов (Xray, Sing-box)
- [v2RayTun](https://apps.apple.com/app/v2raytun/id1533764921) — V2Ray клиент

### Chrome расширения

- [Bitwarden](https://chromewebstore.google.com/detail/bitwarden-password-manage/nngceckbapebfimnlniiiahkandclblb)
- [Video Speed Controller](https://chromewebstore.google.com/detail/video-speed-controller/nffaoalbilbmmfgbnbgppjihopabppdk)
- [AdBlock](https://chromewebstore.google.com/detail/adblock-%E2%80%94-block-ads-acros/gighmmpiobklfepjocnamgkkbiglidom)
- [SponsorBlock](https://chromewebstore.google.com/detail/sponsorblock-for-youtube/mnjggcdmjocbbbhaepdhchncahnbgone)

### Ручная установка (нет в brew)

- [Xnip](https://xnipapp.com/) — скриншоты
- [OwlOCR](https://www.owlocr.com/) — OCR

## Структура репо

```
~/macos-setup/
├── Brewfile                ← все brew-зависимости
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
