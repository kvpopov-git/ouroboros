# Fork adaptation notes

This repository is a fork of [razzant/ouroboros](https://github.com/razzant/ouroboros)
adapted for a **Windows-first / OpenAI-first / Budget-first** personal deploy.

Upstream: https://github.com/razzant/ouroboros  
Fork: https://github.com/kvpopov-git/ouroboros  
Branch: `adapt/openai-first-windows`

## What changed vs upstream

1. **OpenAI-direct defaults** — shipped model slots use `openai::…` prefixes.
   Other providers remain fully supported (Anthropic, OpenRouter, MiniMax,
   Cloud.ru, GigaChat, openai-compatible, local GGUF).
2. **Budget spend profile (default)** — frugal personal-API lane:
   - Main/Light/Fallback: `openai::gpt-5.6-luna`
   - Heavy: empty (uses Main)
   - Review: single `luna` reviewer, advisory
   - `OUROBOROS_RUNTIME_MODE=light`, `OUROBOROS_CONTEXT_MODE=low`
   - Soft caps: `$10` total / `$3` per task, `MAX_ROUNDS=50`, fewer workers/subagents
   - Task acceptance review off; lower reasoning effort; slower BG wakeup
3. **Performance spend profile (optional)** — wizard toggle restores terra/sol,
   max context, advanced runtime, triad review, higher caps.
4. **UI** — Settings Providers tab opens **OpenAI** first; onboarding Budget step
   offers Budget vs Performance cards.
5. **Windows desktop tools** — native skill `skills/windows_computer_use`.

## Why Budget

Comments on the [Habr launch post](https://habr.com/ru/companies/airi/articles/1065428/)
and Hope’s spend show frontier defaults can burn tens–hundreds of millions of
tokens quickly (cache reads included). This fork ships the cheap lane first so
everyday use stays inside a personal budget; opt into Performance deliberately.

## Run on Windows (source + web UI)

```powershell
cd C:\Project\Agent
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python -m pip install -e . --no-deps

# Optional browser tools
python -m playwright install chromium

ouroboros server
# open http://127.0.0.1:8765 — paste OPENAI_API_KEY; keep Budget unless you need Performance
```

## Enable Windows computer use

After first boot, open **Skills** and enable `windows_computer_use`.

## Switching to Performance later

In Settings (or re-run onboarding Budget step):

| Knob | Budget | Performance |
|------|--------|-------------|
| Main | `openai::gpt-5.6-luna` | `openai::gpt-5.6-terra` |
| Heavy | (empty) | `openai::gpt-5.6-sol` |
| Context | `low` | `max` |
| Runtime | `light` | `advanced` |
| Review models | 1× luna | luna,terra,sol |
| Per-task soft | `$3` | `$20` |

## Syncing upstream

```powershell
git remote add upstream https://github.com/razzant/ouroboros.git  # once
git fetch upstream
git merge upstream/main   # expect conflicts around defaults / providers UI / spend profiles
```

Keep fork-specific Budget defaults, spend profiles, and `skills/windows_computer_use`.
