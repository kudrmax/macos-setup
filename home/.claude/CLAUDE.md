# Global CLAUDE.md

## Communication
- Respond in Russian (Русский) always
- Be concise — skip preambles and summaries
- Never do anything git-related without my explicit confirmation (commit, push, rebase, reset, branch, merge, tag)

## Code Style
- Prefer OOP patterns (classes, interfaces, encapsulation)
- Primary languages: Python, Go
- Always use strict typing:
  - Python: type hints everywhere, use `mypy --strict` compatible code
  - Go: leverage the type system fully, no `interface{}` / `any` without justification
- Prefer `dataclasses` or `pydantic` models in Python over plain dicts
- Use named constants over magic numbers
- Prefer composition over inheritance
- For Claude AI integration: use claude-agent-sdk (not anthropic SDK) — it authenticates via Claude Code CLI without requiring an API key
- Always strictly separate frontend and backend — frontend (bot, web UI, CLI) is a replaceable presentation layer, backend logic must never depend on a specific frontend

## Python Environment
- NEVER install project dependencies globally — always use a virtual environment (venv, .venv)
- Before `pip install`, ensure a venv is active; if not — create and activate it first
- Use `python -m venv .venv && source .venv/bin/activate` (or the existing .venv if present)

## Bugs & Broken Tests
- If you discover bugs or broken tests during your work — always report them to the user immediately
- Never skip or deselect broken tests — fix them. Main task first, then fix found bugs right after
- This applies to any test failures: incorrect assertions, outdated expectations, flaky tests — all must be fixed, not ignored

## Homebrew
- На машине настроен Avito brew-прокси (HOMEBREW_BOTTLE_DOMAIN, HOMEBREW_CORE_GIT_REMOTE, HOMEBREW_BREW_GIT_REMOTE)
- Прокси работает только в корпоративной сети/VPN. Вне сети — зависает
- При `brew install` передавать пустые значения для этих переменных, чтобы обойти прокси:
  ```
  HOMEBREW_BOTTLE_DOMAIN="" HOMEBREW_CORE_GIT_REMOTE="" HOMEBREW_BREW_GIT_REMOTE="" brew install <package>
  ```
- НЕ делать unset — переменные нужны в .zprofile для работы в корпоративной сети

## Commits
- Conventional format: feat:, fix:, chore:, docs:, refactor:, test:
- Keep subject lines under 72 chars
- Never include ticket/issue numbers unless I provide them
