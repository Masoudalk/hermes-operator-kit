# Hermes Operator Kit — Windows 11 GUI Automation

Control Windows 11 GUI applications (Notepad, Winver, Charmap, ...) through Telegram single-sentence commands.

## Repository Layout

```
kit/
  lib/          # Python modules: safe_gui_ctl, win_app_ops, safe_gui_launcher, ...
  rules/        # MASTER_RULES.md, OPERATOR_PLAYBOOK.md, MASTER_ENCYCLOPEDIA.md, STARRED_INDEX.md
  config/       # gui_apps.json
  policies/     # STARRED_REGISTRY.jsonl, TIER_POLICY.md
install.ps1     # One-line installer
README.md       # This file
```

## Prerequisites

- Windows 10/11
- Python 3.12+ (tested on Python 3.14.9)
- PowerShell 5.1+

## Installation (one command)

Open PowerShell as Administrator and run:

```powershell
irm https://raw.githubusercontent.com/Masoudalk/hermes-operator-kit/main/install.ps1 | iex
```

Or clone the repository and run locally:

```powershell
git clone https://github.com/Masoudalk/hermes-operator-kit.git
cd hermes-operator-kit
.\install.ps1
```

The installer copies `kit/lib/*`, `kit/rules/*`, `kit/config/*`, `kit/policies/*` and `memory/HANDOFF.md` to `C:\agent-work\`.

## Usage

```powershell
# List available apps
python C:\agent-work\lib\safe_gui_ctl.py list

# Check status
python C:\agent-work\lib\safe_gui_ctl.py status notepad

# Launch + focus
python C:\agent-work\lib\safe_gui_ctl.py launch notepad

# Clear editor
python C:\agent-work\lib\safe_gui_ctl.py clear notepad

# Type text (clipboard-based)
python C:\agent-work\lib\safe_gui_ctl.py type notepad "النص العربي يعمل"

# Verify text readback
python C:\agent-work\lib\safe_gui_ctl.py verify notepad "النص العربي يعمل"

# Regression test
python C:\agent-work\lib\safe_gui_ctl.py test winver

# Close app (WM_CLOSE only)
python C:\agent-work\lib\safe_gui_ctl.py close notepad
```

## Commands

`list | status | launch | clear | type | verify | close | test`

## Safety Rules (OPERATOR_PLAYBOOK.md)

- No `taskkill`, `terminate`, or `kill`. Close only via `WM_CLOSE` through `safe_gui_ctl.py close`.
- Text input only via clipboard paste (`type`), never per-character SendInput.
- Verify uses `VERIFY_SENTINEL` to prevent false positives.
- Real mouse click in editor center before Ctrl+V.
- No secrets or API keys in the repository. Keys go in `.env` only.

## Tests

```powershell
python -m py_compile kit/lib/*.py
python C:\agent-work\lib\safe_gui_ctl.py test winver
```

## License

MIT
