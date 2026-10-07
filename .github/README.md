# macOS setup

Конфиги и инструкция для настройки macOS с нуля. Репо лежит **прямо поверх домашней папки**: git-база в `~/.git-macos-setup`, рабочая папка `~`. Файлы в `~` настоящие, без симлинков и копий. Подробнее в разделе «[Как это работает](#как-это-работает)».

> [!IMPORTANT]
> Если `brew install` падает или зависает на каких-то пакетах (особенно cask) — скорее всего, нужен VPN. Часть ресурсов, с которых brew качает бинари, заблокирована в РФ. Поэтому **Hiddify ставим в первую очередь** (шаг 2), и только потом всё остальное.

## Быстрый старт

Порядок важен: сначала **критический минимум** (без которого нельзя работать вообще), потом **VPN** (без него не стянуть остальное и не запустить Claude Code), потом **всё остальное**.

### 1. Критический минимум

```bash
# 1.1 Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 1.2 Минимальный набор приложений
brew install --cask iterm2 google-chrome telegram claude-code@latest
```

Если что-то из шага 1.2 не ставится — переходи к шагу 2 (VPN), затем вернись и повтори.

### 2. VPN и прокси (обязательно до всего остального)

Без VPN часть API и ресурсов (включая Claude) недоступна. Ставим Hiddify, импортируем профиль, включаем локальный прокси.

Hiddify — клиент для прокси-протоколов (Xray, Sing-box). В brew отсутствует — апстрим не подписывает бинари ([issue #1724](https://github.com/hiddify/hiddify-app/issues/1724)). Запасной вариант: [v2RayTun](https://apps.apple.com/app/v2raytun/id1533764921) (только App Store).

1. Скачать `Hiddify-MacOS.dmg` со страницы [releases](https://github.com/hiddify/hiddify-app/releases/latest) → перетащить в `Applications`.
   При первом запуске: System Settings → Privacy & Security → Open Anyway (приложение не нотаризовано).
2. Импортировать профиль провайдера (ссылка `hiddify://...` или подписка) и включить подключение.
3. Убедиться, что Hiddify слушает прокси на порту `12334`.
   Этот порт по умолчанию, трогать настройки обычно не нужно. Проверить можно в настройках Hiddify в поле с названием типа «Mixed port» / «Порт прокси» — там должно быть `12334`.
   Если порт другой — либо поменяй его в Hiddify на `12334`, либо поправь в `~/.zshrc` переменную `HIDDIFY_PORT` и порт в функциях `vpn-check` / `vpn-on`.
4. Проверить, что прокси реально работает — команда печатает внешний IP:
   ```bash
   curl -s -m 5 -x http://127.0.0.1:12334 https://api.ipify.org
   ```
   Если пусто или ошибка — Hiddify не запущен или порт не `12334`.
5. Для `git clone` и `brew` на следующих шагах включить прокси в текущем терминале:
   ```bash
   export http_proxy="http://127.0.0.1:12334"
   export https_proxy="http://127.0.0.1:12334"
   export all_proxy="socks5://127.0.0.1:12334"
   ```
   Прокси живёт только в этом шелле — в новом терминале его снова нет. После шага 3 то же самое делают функции `vpn-on` / `vpn-off` из `~/.zshrc`, а `vpn-check` повторяет проверку выше.
6. Claude Code запускать **только через команду `cl`** (не через `claude`).
   `cl` — это функция из `~/.zshrc`, которая перед запуском `claude` прокидывает трафик через Hiddify (`127.0.0.1:12334`). Без неё Claude Code не сможет достучаться до API из РФ.
   Команда появится в шелле после шага 3 и перезапуска терминала.

### 3. Развернуть репо с конфигами в `~`

```bash
git clone --bare https://github.com/kudrmax/macos-setup.git ~/.git-macos-setup
git --git-dir=$HOME/.git-macos-setup --work-tree=$HOME checkout
git --git-dir=$HOME/.git-macos-setup --work-tree=$HOME config status.showUntrackedFiles no
```

Вторая команда раскладывает все конфиги по их местам в `~`. Если git ответит `untracked working tree files would be overwritten` — в `~` уже есть файл с таким именем (обычно `.zshrc` или `.gitconfig`, созданные macOS). Убрать его в сторону и повторить:

```bash
mkdir -p ~/.config-before-setup && mv ~/.zshrc ~/.config-before-setup/
```

Третья команда прячет из `git status` всё, что в репо не отслеживается (иначе он покажет всю домашнюю папку).

> [!WARNING]
> `~/.gitconfig` содержит мой email. После разворачивания проверьте `git config user.email`.

### 4. Пакеты

```bash
brew bundle --global
```

Ставит всё из `~/.Brewfile` (он уже лежит в `~` после шага 3): формулы, cask, приложения из App Store (через `mas`, для них нужно быть залогиненным в App Store). Если что-то упало — команду можно безопасно повторить, уже установленное пропускается.

> [!NOTE]
> На рабочей машине с avito brew-прокси (`HOMEBREW_BOTTLE_DOMAIN` и т.п.) — если прокси резолвится, но brew всё равно падает вне корп-сети, запусти команды с пустыми значениями:
> `HOMEBREW_BOTTLE_DOMAIN="" HOMEBREW_CORE_GIT_REMOTE="" HOMEBREW_BREW_GIT_REMOTE="" brew bundle --global`
> НЕ делать `unset` — переменные нужны в `.zprofile` внутри корп-сети.

### 5. Oh-My-Zsh, скиллы Claude Code, Bruno

```bash
RUNZSH=no KEEP_ZSHRC=yes sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
git clone https://github.com/kudrmax/skills.git ~/.claude/skills
git clone https://github.com/kudrmax/bruno-collections.git ~/bruno
```

- `RUNZSH=no` — чтобы установщик Oh-My-Zsh не запускал новый шелл и не обрывал вставленный блок команд.
- Личные скиллы Claude Code живут в отдельном репо и клонируются прямо в `~/.claude/skills` (папки не должно существовать до клона).
- Коллекции запросов Bruno — отдельный приватный репо, путь `~/bruno/avito` прописан в `preferences.json`.

После этого перезапустить терминал.

### 6. Node.js

nvm уже установлен на шаге 4 через brew. Ставим LTS-версию Node.js:

```bash
nvm install --lts
```

### 7. Ручная настройка

См. «[Ручная настройка после установки](#ручная-настройка-после-установки)».

## Как это работает

Git умеет держать свою базу отдельно от рабочей папки. Здесь база лежит в `~/.git-macos-setup`, а рабочая папка — `~`. Поэтому `~/.zshrc`, `~/.config/karabiner/karabiner.json` и остальные конфиги — обычные файлы, которые git отслеживает по их настоящим путям. Приложения пишут в них как в обычные файлы, ломать нечего.

Чтобы не писать флаги `--git-dir` и `--work-tree` каждый раз, в `~/.zshrc` два алиаса:

| Команда | Что делает |
|---|---|
| `lazygit-macos-setup` | lazygit для этого репо: посмотреть изменения, закоммитить, запушить |
| `git-macos-setup add <файл>` | добавить новый конфиг в репо |
| `git-macos-setup status` / `diff` / `pull` / `push` | обычный git для этого репо |

Повседневно:
- Поправил конфиг (руками или через GUI приложения, например Karabiner) → `lazygit-macos-setup` → коммит → push.
- На другой машине: `git-macos-setup pull` перед правками. Если файл менялся с обеих сторон, git скажет об этом и ничего не затрёт.
- Новая программа: `brew install ...`, строка в `~/.Brewfile`, конфиг через `git-macos-setup add`, коммит.
- Проверить полноту: `brew bundle check --global` (чего из Brewfile нет на машине), `brew bundle cleanup --global` (что стоит, но не записано; без `--force` только показывает).

Два правила: не делать `git-macos-setup add -A` или `add .` (добавит всю домашнюю папку) и не класть `*` в `~/.gitignore` (ломает поиск `ripgrep` в других каталогах).

## Ручная настройка после установки

### Шрифты Powerlevel10k

Если не установились автоматически: [ссылка](https://github.com/romkatv/powerlevel10k?tab=readme-ov-file#manual-font-installation)

Перенастроить prompt:
```bash
p10k configure
```

### iTerm2

iTerm2 умеет читать настройки из произвольной папки. Указать ему `~/.config/iterm2` (файл там уже лежит после шага 3), затем перезапустить iTerm2:

```bash
defaults write com.googlecode.iterm2 PrefsCustomFolder -string "$HOME/.config/iterm2"
defaults write com.googlecode.iterm2 LoadPrefsFromCustomFolder -bool true
```

### BTT (Better Touch Tool)

1. Presets → Import presets → `~/.config/btt_preset.bttpreset`
2. Preset (в левом верхнем углу) → удалить default preset
3. Fix 4 Finger Swipe Down: 4 Finger Swipe Down → Application Switcher → Use Gesture Mode

### Karabiner Elements

Конфиг `~/.config/karabiner/karabiner.json` — обычный файл из репо, Karabiner подхватывает его сам. Правки в GUI Karabiner видны в `lazygit-macos-setup` как изменения файла. Если проблемы с `karabiner_grabber` — перезагрузить компьютер.

### Автообновление Homebrew

Устанавливает launchd-агент, который раз в сутки обновляет все формулы и cask-приложения в фоне:

```bash
brew tap domt4/autoupdate
brew trust domt4/autoupdate
brew autoupdate start 86400 --upgrade --cleanup --leaves-only --ac-only
```

`brew trust` обязателен: с 2026 года Homebrew игнорирует команды из сторонних tap, пока tap не помечен доверенным.

Логи: `~/Library/Logs/com.github.domt4.homebrew-autoupdate/com.github.domt4.homebrew-autoupdate.out`

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

Устанавливается через tap (`brew trust` обязателен, см. выше):

```bash
brew tap antopolskiy/tap
brew trust antopolskiy/tap
brew install antopolskiy/tap/kanban-md
```

### Ручная установка (нет в brew)

- [Xnip](https://xnipapp.com/) — скриншоты
- [OwlOCR](https://www.owlocr.com/) — OCR
- [qBittorrent](https://www.qbittorrent.org/download) — cask `qbittorrent` отключён в Homebrew с 2026-09-01 (не проходит проверку Gatekeeper), ставить dmg с сайта

## Структура репо

Корень репо — `~`. В git только перечисленные файлы, остальная домашняя папка не отслеживается.

```
~/
├── .git-macos-setup/       ← git-база репо (не трогать руками)
├── .Brewfile               ← все пакеты: brew, cask, App Store
├── .gitignore
├── .github/
│   ├── README.md           ← этот файл
│   └── CLAUDE.md           ← инструкции Claude Code для работы с этим репо
├── .zshrc, .zshenv, .zprofile, .p10k.zsh, .hushlogin
├── .gitconfig
├── .ipython/profile_default/ipython_config.py
├── .claude/                ← Claude Code: CLAUDE.md, settings.json, statusline.sh
│   └── skills/             ← отдельный репо kudrmax/skills, в этот не входит
├── .config/
│   ├── karabiner/          ← конфиг + правила
│   ├── iterm2/             ← iTerm2 читает отсюда напрямую (PrefsCustomFolder)
│   ├── micro/              ← биндинги редактора micro
│   ├── mpv/                ← скрипты и конфиги для MPV
│   └── btt_preset.bttpreset  ← ручной импорт в BetterTouchTool
├── bruno/                  ← отдельный приватный репо bruno-collections, в этот не входит
└── Library/
    ├── Application Support/
    │   ├── lazygit/config.yml
    │   ├── lazydocker/config.yml
    │   ├── bruno/preferences.json
    │   ├── Code/User/settings.json              ← VS Code
    │   ├── Sublime Text/Packages/User/          ← Sublime Text
    │   └── com.colliderli.iina/                 ← IINA горячие клавиши
    └── Preferences/org.p0deje.Maccy.plist       ← Maccy
```
