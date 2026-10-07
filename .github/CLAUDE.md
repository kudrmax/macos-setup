# macos-setup

Dotfiles repo. Configs live in `home/`, symlinked to `~/` via `sync.sh`.

## Structure
- `home/` — mirrors `~/`, contains actual config files
- `sync.sh` — creates symlinks from `home/` to `~/`, backs up existing files
- BTT exports are skipped by sync (manual import)
- iTerm2 — не симлинкается, а нативно указывает PrefsCustomFolder на репо (сам читает/пишет конфиг оттуда). `sync.sh` сам проставляет `PrefsCustomFolder` + `LoadPrefsFromCustomFolder` через `defaults write`
- Karabiner — симлинки не работают (ломает при записи). `sync.sh` копирует repo→~/ (предупреждает если ~/новее). `copy.sh` копирует ~/→repo (запускать перед коммитом)

## Rules
- Never edit configs outside `home/` — they're symlinks
- After adding new configs: put in `home/` at the same path as `~/`, run `sync.sh`
- Secrets (tokens, credentials) never go in repo — add to `.gitignore`
- All apps and tools should be installed via `brew` / `brew --cask` whenever possible. Manual install only if brew package doesn't exist
