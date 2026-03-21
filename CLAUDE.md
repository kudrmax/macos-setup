# macos-setup

Dotfiles repo. Configs live in `home/`, symlinked to `~/` via `sync.sh`.

## Structure
- `home/` — mirrors `~/`, contains actual config files
- `sync.sh` — creates symlinks from `home/` to `~/`, backs up existing files
- BTT and iTerm2 exports are skipped by sync (manual import)

## Rules
- Never edit configs outside `home/` — they're symlinks
- After adding new configs: put in `home/` at the same path as `~/`, run `sync.sh`
- Secrets (tokens, credentials) never go in repo — add to `.gitignore`
