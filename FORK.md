# Fork adaptation notes

This repository is a fork of [razzant/ouroboros](https://github.com/razzant/ouroboros)
adapted for a **Windows-first / OpenAI-first** personal deploy.

Upstream: https://github.com/razzant/ouroboros  
Fork: https://github.com/kvpopov-git/ouroboros  
Branch: `adapt/openai-first-windows`

## What changed vs upstream

1. **OpenAI-direct defaults** — shipped model slots use `openai::…` prefixes
   (`gpt-5.6-terra` / `sol` / `luna`). Other providers remain fully supported:
   set their API keys and/or switch model ids (`anthropic::…`, OpenRouter slugs,
   `openai-compatible::…`, MiniMax, Cloud.ru, GigaChat, local GGUF).
2. **UI** — Settings Providers tab opens **OpenAI** first; OpenRouter is optional.
3. **Windows desktop tools** — new native skill `skills/windows_computer_use`
   (screenshot + mouse/keyboard via Pillow + Win32). macOS/Linux keep
   `unix_computer_use`.
4. **Provider profile** — empty/minimal setups default to the OpenAI lane;
   OpenAI+OpenRouter without other direct vendors still reports `openai`.

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
# open http://127.0.0.1:8765 — paste OPENAI_API_KEY in the wizard
```

Desktop window (PyWebView launcher) when packaged:

```powershell
.\build_windows.ps1
```

Or from source, `python launcher.py` if launcher deps are installed
(`requirements-launcher.txt`).

## Enable Windows computer use

After first boot, open **Skills** in the UI and enable `windows_computer_use`
(native-seeded; trusted when `OUROBOROS_TRUST_NATIVE_SEEDED_SKILLS=true`).

## Syncing upstream

```powershell
git remote add upstream https://github.com/razzant/ouroboros.git  # once
git fetch upstream
git merge upstream/main   # expect conflicts around defaults / providers UI
```

Keep fork-specific defaults and `skills/windows_computer_use` when resolving.
