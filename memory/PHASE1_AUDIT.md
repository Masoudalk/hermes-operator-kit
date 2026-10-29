# Phase 1 — Audit and Implementation Plan
## Hermes Operator Kit — Linux Port

**Date:** 2026-10-27
**Original repo (READ-ONLY):** https://github.com/Masoudalk/hermes-operator-kit
**Target repo:** https://github.com/Masoudalk/hermes-operator-kit-linux
**Status:** Phase 1 complete — awaiting approval for Phase 2

---

## 1. Source-Tree and Module-Functionality Summary

### Original Repository Structure

```
hermes-operator-kit/
├── install.ps1              # Windows PowerShell installer (self-downloading)
├── install.bat              # Batch wrapper for install.ps1
├── .env.template            # Environment template
├── .gitignore               # Excludes .env, *.bak-*, lib.bak-*
├── docs/
│   └── README.md            # Documentation with SHA256 verification
└── kit/
    ├── config/
    │   └── gui_apps.json    # App registry (name, exe path, process name)
    ├── lib/
    │   ├── safe_gui_launcher.py   # Duplicate-prevention launcher (Popen + PID tracking)
    │   ├── win_app_ops.py         # Windows window tracking, focus, clipboard, mouse
    │   ├── safe_gui_ctl.py        # CLI: launch/status/close/type/verify/clear/test
    │   ├── action_executor.py     # High-level workflow executor (pywinauto)
    │   ├── element_locator.py     # UI element finder (pywinauto UIA/Win32)
    │   ├── mouse_controller.py    # Mouse control with tracking (ctypes)
    │   └── vision_layer.py        # Screenshot capture (pyautogui/PIL)
    ├── rules/
    │   ├── MASTER_RULES.md        # 12-line rule set
    │   └── OPERATOR_PLAYBOOK.md   # 14-point Windows 11 playbook
    └── skills/
        └── safe-gui-launcher/
            └── SKILL.md            # Skill definition with playbook pointer
```

### Module Functionality

| Module | Lines | Purpose |
|--------|-------|---------|
| `safe_gui_launcher.py` | 162 | Prevent duplicate GUI app launches; Popen + PID tracking; WM_CLOSE for close |
| `win_app_ops.py` | 241 | Windows window enumeration, focus (AttachThreadInput), clipboard (CF_UNICODETEXT), mouse (mouse_event), real_click, click_window_center, send_delete |
| `safe_gui_ctl.py` | 291 | CLI controller: list, status, launch, close, test (duplicate check), type (clipboard paste), verify (sentinel clipboard), clear (Ctrl+A+Delete) |
| `action_executor.py` | 170 | High-level workflow: open, connect, find window, click, type, invoke, close; tracks mouse deviation |
| `element_locator.py` | 106 | pywinauto-based element finder: by process_id, path, title, class_name, auto_id, control_type |
| `mouse_controller.py` | 109 | Smooth mouse movement, click, double-click, tracking with deviation stats |
| `vision_layer.py` | 65 | Screenshot capture via pyautogui/PIL, base64 encoding |
| `install.ps1` | 53 | Self-downloading PowerShell installer; copies kit/ to C:\agent-work |
| `install.bat` | 2 | Batch wrapper calling install.ps1 |
| `gui_apps.json` | 7 | App registry: name, exe path, process name |
| `OPERATOR_PLAYBOOK.md` | 14 | 12-point Windows 11 operational playbook |
| `MASTER_RULES.md` | 11 | Core rules (no self-modification, no model changes, etc.) |
| `SKILL.md` | 145 | Skill definition with playbook pointer |

---

## 2. Windows-Specific APIs, Commands, and Dependencies

### Windows APIs (ctypes.windll.user32 / kernel32)

| API | Used In | Purpose |
|-----|---------|---------|
| `EnumWindows` | win_app_ops, safe_gui_launcher | Enumerate top-level windows |
| `GetWindowThreadProcessId` | win_app_ops, safe_gui_launcher | Map HWND → PID |
| `IsWindowVisible` / `IsIconic` | win_app_ops, safe_gui_launcher | Window state checks |
| `ShowWindow` (SW_RESTORE) | win_app_ops | Restore minimized windows |
| `GetForegroundWindow` | win_app_ops | Get current foreground window |
| `AttachThreadInput` | win_app_ops | Gain foreground rights without Alt trick |
| `SetForegroundWindow` | win_app_ops | Set foreground window |
| `keybd_event` (VK_MENU) | win_app_ops | Alt-key focus fallback |
| `PostMessageW` (WM_CLOSE) | win_app_ops, safe_gui_launcher | Close windows gracefully |
| `GetWindowRect` | win_app_ops | Get window coordinates for clicking |
| `GetSystemMetrics` | win_app_ops | Screen dimensions for mouse_event |
| `mouse_event` | win_app_ops, mouse_controller | Move/click mouse (absolute coordinates) |
| `SetCursorPos` | mouse_controller | Set mouse position |
| `GetCursorPos` | mouse_controller | Read mouse position |
| `OpenClipboard` / `EmptyClipboard` / `SetClipboardData` / `GetClipboardData` / `CloseClipboard` | win_app_ops | Clipboard (CF_UNICODETEXT) |
| `GlobalAlloc` / `GlobalLock` / `GlobalUnlock` | win_app_ops | Memory allocation for clipboard |
| `keybd_event` (VK_CONTROL, VK_DELETE) | win_app_ops | Ctrl+A/C/V, Delete |

### Windows Commands

| Command | Purpose |
|---------|---------|
| `subprocess.Popen([exe])` | Launch Windows executables |
| `psutil.process_iter` | Process enumeration (cross-platform, but used for .exe names) |
| `Path(exe).name` | Extract .exe filename |

### Windows Dependencies

| Dependency | Purpose | Windows-Only? |
|-----------|---------|---------------|
| `ctypes` (windll) | Windows API calls | Yes |
| `pywinauto` | UI automation (UIA/Win32 backends) | Yes |
| `pyautogui` | Screenshots, mouse (used in vision_layer) | Partially (has Linux support but limited) |
| `psutil` | Process management | No (cross-platform) |
| `PIL/Pillow` | Image processing | No (cross-platform) |

### Windows-Specific Paths

| Path | Purpose |
|------|---------|
| `C:\agent-work\lib\` | Library directory |
| `C:\agent-work\config\gui_apps.json` | App registry |
| `C:\agent-work\rules\` | Rules and playbook |
| `C:\Windows\System32\*.exe` | Built-in app executables |
| `C:\Users\MA\AppData\Local\hermes\skills\` | Hermes skills directory |

---

## 3. Reuse / Replace / Rewrite Table

| Module | Decision | Rationale |
|--------|----------|-----------|
| `safe_gui_launcher.py` | **REWRITE** | Uses `ctypes.windll` for window detection, `subprocess.Popen([exe])` with .exe paths, `_wait_for_window` via EnumWindows. Core logic (duplicate prevention, WM_CLOSE) needs Linux equivalents (xdotool/wmctrl, SIGTERM). |
| `win_app_ops.py` | **REWRITE** | Entirely Windows API (ctypes.windll.user32/kernel32). Every function needs Linux replacement: `toplevel_windows` → `xdotool search --pid` or `wmctrl -lp`; `restore_and_focus` → `xdotool windowactivate`; `set_clipboard_text` → `xclip`/`xsel`/`wl-copy`; `real_click` → `xdotool click` or `ydotool`; `send_ctrl_v` → `xdotool key ctrl+v`. |
| `safe_gui_ctl.py` | **REUSE (structure)** | CLI structure, command parsing, output format are reusable. Need to replace Windows-specific imports and paths. Config path, app registry format need Linux adaptation. |
| `action_executor.py` | **REWRITE** | Uses `pywinauto` (Windows-only), `subprocess.Popen([exe_path])`, `proc.kill()`. Needs Linux AT-SPI or xdotool-based replacement. |
| `element_locator.py` | **REWRITE** | Entirely `pywinauto` (Desktop, Application, ElementNotFoundError). Needs AT-SPI (pyatspi) or dogtail for Linux. |
| `mouse_controller.py` | **REWRITE** | Uses `ctypes.windll.user32` (GetCursorPos, SetCursorPos, mouse_event). Needs `xdotool` or `python-xlib` for X11; `ydotool` for Wayland. |
| `vision_layer.py` | **REUSE (mostly)** | PIL/Pillow is cross-platform. Screenshot capture needs replacement: `pyautogui` → `mss` (cross-platform) or `scrot`/`grim` (Linux). |
| `install.ps1` | **REPLACE** | PowerShell installer. Need `install.sh` (bash) for Linux. |
| `install.bat` | **REPLACE** | Windows batch wrapper. Not needed on Linux. |
| `gui_apps.json` | **ADAPT** | Windows .exe paths → Linux binary paths (e.g., `/usr/bin/gedit`, `/usr/bin/kate`). |
| `OPERATOR_PLAYBOOK.md` | **ADAPT** | Windows 11-specific rules → Linux (X11/Wayland) operational rules. |
| `MASTER_RULES.md` | **REUSE** | Generic rules, no platform-specific content. |
| `SKILL.md` | **ADAPT** | References Windows paths and safe_gui_ctl.py; needs Linux paths. |

---

## 4. Proposed Linux Project Structure

```
hermes-operator-kit-linux/
├── install.sh                  # Bash installer (detects distro, installs deps)
├── install.bat                 # (not needed, omit)
├── .env.template
├── .gitignore
├── docs/
│   ├── README.md               # Linux installation and usage guide
│   ├── X11_GUIDE.md            # X11-specific notes
│   └── WAYLAND_GUIDE.md        # Wayland limitations and workarounds
├── kit/
│   ├── config/
│   │   └── gui_apps.json       # Linux app registry (binary paths)
│   ├── lib/
│   │   ├── safe_gui_launcher.py    # Cross-platform launcher (subprocess + PID)
│   │   ├── linux_app_ops.py        # X11/Wayland window/clipboard/mouse ops
│   │   ├── safe_gui_ctl.py         # CLI controller (adapted for Linux)
│   │   ├── action_executor.py      # High-level workflow (AT-SPI/pyatspi)
│   │   ├── element_locator.py      # AT-SPI element finder
│   │   ├── mouse_controller.py     # xdotool/ydotool mouse control
│   │   └── vision_layer.py         # Screenshot via mss/grim
│   ├── rules/
│   │   ├── MASTER_RULES.md        # Reused as-is
│   │   └── OPERATOR_PLAYBOOK.md   # Linux-adapted playbook
│   └── skills/
│       └── safe-gui-launcher/
│           └── SKILL.md            # Linux-adapted skill
├── tests/
│   ├── test_launch.py
│   ├── test_type_verify.py
│   └── test_close.py
└── requirements.txt            # Python dependencies
```

---

## 5. Phased Implementation Plan

### Phase 2: Core Architecture (X11-first)
- Create `linux_app_ops.py` with X11 backend:
  - `all_pids(process_name)` — psutil (cross-platform, reuse)
  - `toplevel_windows(pid)` — `xdotool search --pid` or `wmctrl -lp`
  - `app_pids(process_name)` — filter PIDs with windows
  - `restore_and_focus(pid)` — `xdotool windowactivate`
  - `wait_for_windowed_pid(...)` — poll xdotool
  - `launch_app_windowed(...)` — subprocess.Popen + wait_for_windowed_pid
  - `close_app_windows(...)` — `xdotool windowclose` or `wmctrl -c`
  - `set_clipboard_text(text)` — `xclip -selection clipboard` or `xsel`
  - `get_clipboard_text()` — `xclip -selection clipboard -o`
  - `send_ctrl_v/a/c()` — `xdotool key ctrl+v` etc.
  - `real_click(x, y)` — `xdotool mousemove --sync x y click 1`
  - `click_window_center(pid, frac_y)` — get window geometry via xdotool, compute center, real_click
  - `send_delete()` — `xdotool key Delete`
- Adapt `safe_gui_ctl.py` for Linux paths and imports
- Create `install.sh` (bash) with distro detection and dependency installation
- Create `requirements.txt`

### Phase 3: Wayland Support
- Detect session type (`$XDG_SESSION_TYPE`)
- If Wayland: use `wl-copy`/`wl-paste` for clipboard, `ydotool` for mouse/keyboard
- Document limitations: window enumeration restricted, focus may not work, some apps run under XWayland
- Implement fallback: if Wayland and tool unavailable, report `UNSUPPORTED_ON_WAYLAND`

### Phase 4: Security
- Input validation for app keys and text
- No shell=True in subprocess calls
- Clipboard content sanitization
- Permission checks (xdotool/ydotool may need uinput access)

### Phase 5: Testing
- Unit tests for linux_app_ops functions
- Integration tests: launch, type, verify, close for gedit/kate/gedit
- Duplicate-prevention tests
- Wayland limitation documentation

### Phase 6: Installation
- `install.sh` with:
  - Distro detection (apt/dnf/pacman)
  - Dependency installation (python3, psutil, xdotool, xclip, wmctrl)
  - Optional Wayland tools (wl-clipboard, ydotool)
  - Copy kit files to ~/agent-work or /opt/agent-work
  - Idempotency check

### Phase 7: Documentation
- README.md with Linux install command
- X11_GUIDE.md
- WAYLAND_GUIDE.md
- Known limitations document

---

## 6. Dependencies and Reasons

| Dependency | Reason | X11 | Wayland |
|-----------|--------|-----|---------|
| `python3` (≥3.10) | Runtime for all scripts | ✅ | ✅ |
| `psutil` | Process enumeration (cross-platform) | ✅ | ✅ |
| `xdotool` | Window management, keyboard/mouse simulation (X11) | ✅ | ❌ (XWayland only) |
| `wmctrl` | Window listing and management (X11) | ✅ | ❌ |
| `xclip` | Clipboard access (X11) | ✅ | ❌ |
| `xsel` | Alternative clipboard (X11) | ✅ | ❌ |
| `wl-clipboard` (wl-copy/wl-paste) | Clipboard access (Wayland) | ❌ | ✅ |
| `ydotool` | Mouse/keyboard simulation (Wayland) | ❌ | ✅ (requires uinput) |
| `mss` | Cross-platform screenshots | ✅ | ✅ |
| `Pillow` | Image processing | ✅ | ✅ |
| `at-spi2-core` / `pyatspi` | Accessibility tree (element location) | ✅ | ✅ (limited) |

---

## 7. Risks, Permission Requirements, and Wayland Limitations

### Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Wayland security model blocks window enumeration | High | Detect session type; report UNSUPPORTED for restricted operations |
| ydotool requires uinput device access | Medium | Document setup; provide udev rules |
| Different desktop environments (GNOME, KDE, XFCE) have different window managers | Medium | Test on GNOME (most common); document DE-specific notes |
| App paths vary by distro | Medium | Use `which` / `command -v` to resolve binaries |
| Clipboard tools differ (xclip vs wl-copy) | Low | Auto-detect available tool |
| No universal "WM_CLOSE" equivalent on Linux | Medium | Use `xdotool windowclose` (X11) or `kill` with SIGTERM (fallback) |

### Permission Requirements

| Tool | Permission | Setup |
|------|-----------|-------|
| `xdotool` | X11 session access | Usually available if `$DISPLAY` is set |
| `ydotool` | `/dev/uinput` write access | `sudo usermod -aG input $USER` + udev rule |
| `wl-copy` | Wayland session access | Usually available if `$WAYLAND_DISPLAY` is set |
| `scrot`/`grim` | Display server access | Usually available |

### Wayland Limitations (Honest Assessment)

1. **Window enumeration**: Wayland compositors do not expose window lists to arbitrary clients. `xdotool` and `wmctrl` do NOT work on native Wayland (only under XWayland).
2. **Window focus**: `SetForegroundWindow` equivalent does not exist on Wayland. Apps cannot steal focus.
3. **Global mouse/keyboard simulation**: `ydotool` works via `/dev/uinput` but requires root or uinput group membership.
4. **Clipboard**: `wl-copy`/`wl-paste` work but only for the focused Wayland client in some compositors.
5. **Screenshots**: `grim` works on wlroots-based compositors; GNOME requires `gnome-screenshot` or D-Bus portal.
6. **Application launching**: Works via subprocess, but window tracking is severely limited.

**Recommendation:** Target X11 first (full functionality). For Wayland, provide best-effort support with clear `UNSUPPORTED_ON_WAYLAND` reporting for operations that cannot be performed.

---

## 8. Acceptance-Test Checklist

### X11 (Full Support)

- [ ] `install.sh` runs successfully on Ubuntu 24.04 / Pop!_OS 24.04
- [ ] All dependencies installed automatically
- [ ] `safe_gui_ctl.py list` shows registered apps
- [ ] `safe_gui_ctl.py launch gedit` → RESULT=LAUNCHED, FOCUSED=true
- [ ] `safe_gui_ctl.py clear gedit` → RESULT=CLEARED
- [ ] `safe_gui_ctl.py type gedit "test text"` → RESULT=TYPED, CLIPBOARD_SET=True
- [ ] `safe_gui_ctl.py verify gedit "test text"` → RESULT=VERIFIED, MATCH=true
- [ ] `safe_gui_ctl.py close gedit` → RESULT=CLOSED
- [ ] Duplicate launch blocked (RESULT=ALREADY_RUNNING)
- [ ] `safe_gui_ctl.py test gedit` → RESULT=PASS
- [ ] Screenshot captured and text visible
- [ ] No .env, auth.json, MASTER_ENCYCLOPEDIA.md, or .bak files in repo

### Wayland (Best-Effort)

- [ ] Session type detected correctly (`$XDG_SESSION_TYPE`)
- [ ] Clipboard operations work via wl-copy/wl-paste
- [ ] Mouse/keyboard simulation works via ydotool (if uinput available)
- [ ] Window operations report `UNSUPPORTED_ON_WAYLAND` when not possible
- [ ] No crashes on Wayland-only session
- [ ] Documentation clearly states Wayland limitations

### Cross-Cutting

- [ ] No Windows-specific code paths executed on Linux
- [ ] No modifications to original repository
- [ ] All file paths use forward slashes
- [ ] UTF-8 without BOM
- [ ] Idempotent install (running twice doesn't break anything)
- [ ] HANDOFF.md updated after each phase

---

## Summary

The original project is a **Windows 11-only** GUI automation kit using `ctypes.windll`, `pywinauto`, and PowerShell. A Linux port requires:

1. **Complete rewrite** of `win_app_ops.py` → `linux_app_ops.py` (X11 tools + Wayland fallbacks)
2. **Complete rewrite** of `element_locator.py` and `action_executor.py` (AT-SPI instead of pywinauto)
3. **Complete rewrite** of `mouse_controller.py` (xdotool/ydotool instead of mouse_event)
4. **Adaptation** of `safe_gui_ctl.py` (paths, imports, app registry)
5. **New installer** (`install.sh` instead of `install.ps1`)
6. **New documentation** (X11/Wayland guides, limitations)

**Recommended approach:** X11-first with full functionality, Wayland best-effort with honest limitation reporting.

---

**Phase 1 complete. Awaiting approval to proceed to Phase 2.**
