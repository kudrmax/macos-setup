# macOS setup

Конфиги и инструкции для настройки macOS с нуля. Конфиги хранятся в `home/` и симлинкаются в `~/` скриптом `sync.sh`.

> [!IMPORTANT]
> Если `brew install` падает или зависает на каких-то пакетах (особенно cask) — скорее всего, нужен VPN. Часть ресурсов, с которых brew качает бинари, заблокирована в РФ. Поэтому **Hiddify ставим в первую очередь** (шаг 2), и только потом всё остальное.

## Быстрый старт

Порядок важен: сначала **критический минимум** (без которого нельзя работать вообще), потом **VPN** (без него не стянуть остальное и не запустить Claude Code), потом **всё остальное**.

### 1. Критический минимум

Без этого невозможно продолжить: Homebrew, репо с конфигами, терминал, браузер, мессенджер, Claude Code.

```bash
# 1.1 Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 1.2 Склонировать репо
git clone https://github.com/kudrmax/macos-setup ~/macos-setup

# 1.3 Минимальный набор приложений
brew install --cask iterm2 google-chrome telegram claude-code
```

Если что-то из шага 1.3 не ставится — переходи к шагу 2 (VPN), затем вернись и повтори.

### 2. VPN и прокси (обязательно до всего остального)

Без VPN часть API и ресурсов (включая Claude) недоступна. Ставим Hiddify, импортируем профиль, включаем локальный прокси.

Hiddify — клиент для прокси-протоколов (Xray, Sing-box). В brew отсутствует — апстрим не подписывает бинари ([issue #1724](https://github.com/hiddify/hiddify-app/issues/1724)). Запасной вариант: [v2RayTun](https://apps.apple.com/app/v2raytun/id1533764921) (только App Store).

1. Скачать `Hiddify-MacOS.dmg` со страницы [releases](https://github.com/hiddify/hiddify-app/releases/latest) → перетащить в `Applications`.
   При первом запуске: System Settings → Privacy & Security → Open Anyway (приложение не нотаризовано).
2. Импортировать профиль провайдера (ссылка `hiddify://...` или подписка) и включить подключение.
3. Убедиться, что Hiddify слушает прокси на порту `12334`.
   Этот порт по умолчанию, трогать настройки обычно не нужно. Проверить можно в настройках Hiddify в поле с названием типа «Mixed port» / «Порт прокси» — там должно быть `12334`.
   Если порт другой — либо поменяй его в Hiddify на `12334`, либо поправь значение в функции `cl()` (`home/.zshrc:108`).
4. Claude Code запускать **только через команду `cl`** (не через `claude`).
   `cl` — это функция из `home/.zshrc`, которая перед запуском `claude` прокидывает трафик через Hiddify (`127.0.0.1:12334`). Без неё Claude Code не сможет достучаться до API из РФ.
   Команда появится в шелле после шага 3 ниже (`sync.sh` + перезапуск терминала).
5. Проверить, что VPN реально работает (после шага 3, когда `.zshrc` подхватится):
   ```bash
   vpn-check   # курлит через 127.0.0.1:12334 и печатает внешний IP
   ```
   Если `FAIL` — Hiddify не запущен или порт не `12334`.

   Для обычных команд (`curl`, `git`, `pip` и т.д.) прокси в шелле не активен по умолчанию — его надо включать вручную в конкретном терминале:
   ```bash
   vpn-on    # включить прокси в текущем шелле
   vpn-off   # выключить
   ```
   Если нужно без функций, ровно то же самое делается руками:
   ```bash
   export http_proxy="http://127.0.0.1:12334"
   export https_proxy="http://127.0.0.1:12334"
   export all_proxy="socks5://127.0.0.1:12334"
   ```
   Прокси живёт только в текущем шелле — в новом терминале его снова нет.

### 3. Oh-My-Zsh и симлинки

```bash
sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
cd ~/macos-setup && ./sync.sh
```

> [!WARNING]
> `home/.gitconfig` содержит мой email. После `sync.sh` проверьте `git config user.email`.

### 4. Полная установка пакетов

См. раздел «[Установка пакетов](#установка-пакетов)» ниже — одним блоком, копируется целиком.

### 5. Ручная настройка

См. «[Ручная настройка после установки](#ручная-настройка-после-установки)».

## Установка пакетов

Весь список — одним блоком, разбит комментариями по категориям. Если какой-то `brew install` упал — блок можно безопасно перезапустить, brew пропустит уже установленные.

```bash
# === Terminal ===
brew install powerlevel10k zsh-autosuggestions zsh-syntax-highlighting \
  zsh-history-substring-search zsh-you-should-use fzf atuin zoxide micro
brew install --cask iterm2

# === Современные замены CLI-утилит ===
brew install bat       # cat
brew install eza       # ls
brew install fd        # find
brew install ripgrep   # grep
brew install trash     # rm (в корзину)
brew install jq        # JSON парсинг

# === Git ===
brew install lazygit git-delta

# === Docker ===
brew install lazydocker

# === Языки и рантаймы ===
brew install go nvm libpq python

# === Медиа ===
brew install yt-dlp

# === Утилиты ===
brew install --cask maccy bitwarden appcleaner bettertouchtool \
  karabiner-elements sublime-text

# === AI ===
brew install --cask claude claude-code

# === Приложения ===
brew install --cask google-chrome telegram iina todoist-app obsidian \
  morgen yandex-music arc qbittorrent bruno
```

> [!NOTE]
> На рабочей машине с avito brew-прокси (`HOMEBREW_BOTTLE_DOMAIN` и т.п.) — если прокси резолвится, но brew всё равно падает вне корп-сети, запусти команды с пустыми значениями:
> `HOMEBREW_BOTTLE_DOMAIN="" HOMEBREW_CORE_GIT_REMOTE="" HOMEBREW_BREW_GIT_REMOTE="" brew install ...`
> НЕ делать `unset` — переменные нужны в `.zprofile` внутри корп-сети.

### Проверка установленных пакетов

Скрипт ниже печатает, каких пакетов из требуемого набора не хватает. Копируется и запускается целиком:

```bash
FORMULAE=(
  powerlevel10k zsh-autosuggestions zsh-syntax-highlighting
  zsh-history-substring-search zsh-you-should-use fzf atuin zoxide micro
  bat eza fd ripgrep trash jq
  lazygit git-delta lazydocker
  go nvm libpq python
  yt-dlp
)
CASKS=(
  iterm2
  maccy bitwarden appcleaner bettertouchtool karabiner-elements sublime-text
  claude claude-code
  google-chrome telegram iina todoist-app obsidian morgen yandex-music arc qbittorrent bruno
)

missing_formulae=()
missing_casks=()
for f in "${FORMULAE[@]}"; do
  brew list --formula "$f" &>/dev/null || missing_formulae+=("$f")
done
for c in "${CASKS[@]}"; do
  brew list --cask "$c" &>/dev/null || missing_casks+=("$c")
done

if (( ${#missing_formulae[@]} == 0 && ${#missing_casks[@]} == 0 )); then
  echo "✓ Все пакеты установлены"
else
  (( ${#missing_formulae[@]} )) && echo "✗ Не хватает формул: ${missing_formulae[*]}"
  (( ${#missing_casks[@]} ))    && echo "✗ Не хватает cask:    ${missing_casks[*]}"
fi
```

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

### Chrome расширения

- [Bitwarden](https://chromewebstore.google.com/detail/bitwarden-password-manage/nngceckbapebfimnlniiiahkandclblb)
- [Video Speed Controller](https://chromewebstore.google.com/detail/video-speed-controller/nffaoalbilbmmfgbnbgppjihopabppdk)
- [AdBlock](https://chromewebstore.google.com/detail/adblock-%E2%80%94-block-ads-acros/gighmmpiobklfepjocnamgkkbiglidom)
- [SponsorBlock](https://chromewebstore.google.com/detail/sponsorblock-for-youtube/mnjggcdmjocbbbhaepdhchncahnbgone)

### Сон и экран

System Settings → **Battery** → **Options** → **Prevent automatic sleeping on power adapter when the display is off** → **On**

На зарядке мак не уходит в сон, даже если экран погас. Долгие задачи (сборки, загрузки, ssh-сессии, docker-контейнеры) не прерываются. На батарее не действует — там мак всё равно уснёт по таймеру (`Lock Screen → Turn display off on battery when inactive`), отключить это через GUI нельзя.

### Docker без Docker Desktop (опционально)

Если нужен `docker` в терминале, но не хочется ставить Docker Desktop (Electron-GUI, ~2 GB на диске, 1–2 GB RAM в простое, лицензия для компаний) — ставим **colima**. Это лёгкая Lima VM с docker-демоном внутри: бинарники ~200 MB, RAM только пока VM запущена, GUI нет.

```bash
brew install docker docker-compose colima
mkdir -p ~/.docker/cli-plugins
ln -sfn /opt/homebrew/opt/docker-compose/bin/docker-compose ~/.docker/cli-plugins/docker-compose
```

- `docker` — только CLI-клиент (без Desktop)
- `docker-compose` — плагин compose v2 (вызывается как `docker compose`)
- `colima` — VM с docker-демоном

> Симлинк обязателен: brew ставит `docker-compose` отдельным бинарником и не регистрирует его как Docker CLI plugin. Без симлинка `docker compose ...` падает с `unknown shorthand flag`, потому что docker не видит подкоманду `compose` и парсит флаги сам. Проверить: `docker compose version` должен вернуть версию.

Запуск (по умолчанию 2 CPU / 2 GB RAM, можно задать сразу):

```bash
colima start --cpu 4 --memory 8 --disk 60
```

Проверка:

```bash
docker context ls    # должен быть активен colima
docker run hello-world
```

Управление:

```bash
colima stop      # остановить VM (RAM освобождается полностью)
colima status
colima delete    # снести
```

Автостарт при логине (опционально):

```bash
brew services start colima
```

### kanban-md

Kanban-доска в markdown-файлах: https://github.com/antopolskiy/kanban-md

Устанавливается через tap:

```bash
brew tap antopolskiy/tap
brew install antopolskiy/tap/kanban-md
```

### Ручная установка (нет в brew)

- [Xnip](https://xnipapp.com/) — скриншоты
- [OwlOCR](https://www.owlocr.com/) — OCR

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
