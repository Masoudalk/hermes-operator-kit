---
name: safe-gui-launcher
description: Safely launch GUI apps without duplicates or shell. Includes clipboard typing, verify, clear, and Windows 11 operation rules.
version: 1.0.0
author: Local Operator
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [gui, automation, subprocess, process-management, pid-tracking, duplicate-prevention]
    category: desktop
    related_skills: [gui-process-management, computer-use]
---

# Safe GUI Launcher (Project Mandatory)

Use `C:/agent-work/lib/safe_gui_launcher.py` and `launch_app_safely(app_name, exe_path_or_command)` for every GUI app launch in this project.

Forbidden: direct `subprocess.Popen`, `shell=True`, `Application().start()` as first launch path, fallback launcher, mouse movement, clicking, typing, screenshots, LLM calls inside launch.

If result is False, stop and report message. Do not retry. Do not kill existing process. Do not open another window.

Success requires ok True, PID in message, and log line in `last_launched_apps.txt`.

## Mandatory Close Rule

Use `close_app_safely(app_name, process_name)` to close GUI apps launched by this project. It sends `WM_CLOSE` only. Do not use `Stop-Process`, `taskkill`, `proc.terminate()`, `psutil.kill()`, or `TerminateProcess`. If close returns False, stop and report.

## Deterministic Controller

Prefer `C:/agent-work/lib/safe_gui_ctl.py test <winver|charmap|notepad>` for end-to-end GUI launch tests. It launches, verifies duplicate blocking, closes via WM_CLOSE, and prints RESULT=PASS/FAIL. Do not replace it with custom Python, direct Popen, screenshots, computer_use, or extra terminal commands.

## Post-Execution Rule

After running safe_gui_launcher or safe_gui_ctl and receiving RESULT=PASS or RESULT=FAIL, do not run additional terminal commands, screenshots, computer_use, vision, browser, file_write, read_file, or code_execution. Report the result only.

## Mandatory Controller Interface

For any GUI operation in this project, use only `C:/agent-work/lib/safe_gui_ctl.py` with commands: `list`, `status`, `launch`, `close`, `test`, `type`, `verify`, `clear`.

## Free-Form Task Directive (Stage 23+)

When receiving a free-form natural-language task from Telegram:
1. Understand the task without explicit commands from the user.
2. Plan in ≤3 lines in the first reply.
3. Execute using: safe_gui_ctl.py for apps, computer_use for vision/general clicks, terminal/file tools for files/checks, web tools for internet.
4. Verify with evidence before declaring "done".
5. Update HANDOFF.md at the end of every task.
6. Send a concise report with keys, and at least one screenshot if the task involves UI, with SCREENSHOT_SENT=yes or no explicitly.

## Operator Playbook

Full Windows 11 GUI operation lessons are in `C:/agent-work/rules/OPERATOR_PLAYBOOK.md`. Key rules:
- Always clear editor before typing (stale session content).
- Always click window center before Ctrl+V (programmatic focus alone is insufficient).
- Always use sentinel clipboard pattern for verify (set VERIFY_SENTINEL before Ctrl+A/Ctrl+C).
- Never leave SCREENSHOT_SENT empty in reports — fill yes or no.

## Windows 11 App Registration

The controller's `BUILTIN_APPS` dict includes `notepad` (Windows 11 Store app) alongside `winver` and `charmap`. The `win_app_ops.py` module handles the stub-process issue by tracking only PIDs that own visible top-level windows. When adding new Windows 11 Store apps, register them in `BUILTIN_APPS` with the correct exe path and process name.

## Windows 11 Process Model Pitfall

On Windows 11, modern Store apps (Notepad, Winver, Charmap) use a launcher stub: `subprocess.Popen` returns a stub PID that has **no top-level window**. The actual windowed process is a separate PID spawned by the stub. Tracking the stub PID leads to false "no window" failures and orphaned stub processes.

**Rule:** Always enumerate top-level windows via `EnumWindows` filtered by process ID to find the real windowed process. Use `app_pids()` (in `win_app_ops.py`) which returns only PIDs that own visible top-level windows. Never treat the `Popen` return PID as the app's window owner.

**Close rule:** `WM_CLOSE` must be posted to the visible top-level window HWNDs of the windowed process, not the stub. `close_app_windows()` in `win_app_ops.py` handles this correctly.

**Duplicate detection:** Check `app_pids()` (windowed PIDs only) for duplicate prevention, not `all_pids()` which includes stubs.

**Focus rule:** Use `AttachThreadInput` to attach to the foreground window's thread before calling `SetForegroundWindow`. The Alt key trick (`keybd_event(VK_MENU)`) is unreliable on Windows 11 and can arm menu bars. `AttachThreadInput` is the correct approach: attach, set foreground, detach. Fall back to the Alt key trick only if AttachThreadInput fails.

## Clipboard-Based Typing

For reliable text entry into Windows 11 GUI apps (Notepad), use clipboard-based typing instead of synthetic keystrokes:

1. `set_clipboard_text(text)` — sets clipboard via Win32 API
2. `send_ctrl_v()` — pastes clipboard content
3. `send_ctrl_a()` + `send_ctrl_c()` — selects all and copies back
4. `get_clipboard_text()` — reads clipboard to verify

**Verification:** After typing, read back the clipboard and compare to expected text. If mismatch, report `RESULT=MISMATCH`.

**Controller commands:** `safe_gui_ctl.py type <app-key> <text...>` and `safe_gui_ctl.py verify <app-key> <expected...>`.

## ctypes argtypes Pitfall (64-bit)

In 64-bit Python, Win32 handle-returning functions need explicit `restype` and `argtypes` or you get `OverflowError: int too long to convert`. Required for: `GlobalLock`, `GlobalAlloc`, `SetClipboardData`, `OpenClipboard`, `GetClipboardData`, `GlobalUnlock`.

Set these before calling:
```python
kernel32.GlobalAlloc.restype = ctypes.c_void_p
kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
user32.OpenClipboard.argtypes = [ctypes.c_void_p]
user32.OpenClipboard.restype = ctypes.c_bool
user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
user32.SetClipboardData.restype = ctypes.c_void_p
user32.GetClipboardData.argtypes = [ctypes.c_uint]
user32.GetClipboardData.restype = ctypes.c_void_p
```

## Real Mouse Click Before Typing

Windows 11 Notepad requires a real mouse click in the editor area before synthetic keyboard input (Ctrl+V) will register. Programmatic focus (SetForegroundWindow) alone is insufficient — the editor control must receive a mouse click to activate its input context.

**Rule:** Call `click_window_center(pid, frac_y=0.6)` (real mouse_event, not simulated) before sending Ctrl+V. The `real_click` function uses `MOUSEEVENTF_ABSOLUTE` with normalized coordinates (0-65535 range) based on screen dimensions from `GetSystemMetrics`.

**Pitfall:** `mouse_event` also needs `argtypes` set on 64-bit Python:
```python
user32.mouse_event.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_ulong]
user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int
```

## Sentinel Clipboard Pattern for Verify

The verify command has a circular problem: it sets clipboard to expected text, then does Ctrl+A, Ctrl+C to copy the editor content. If the editor was not actually focused or the selection failed, Ctrl+C does nothing and the clipboard retains the sentinel value. This creates a false positive (MATCH=true against sentinel).

**Rule:** Before verify, set clipboard to `"VERIFY_SENTINEL"`. After Ctrl+A + Ctrl+C, read clipboard. If it still equals `"VERIFY_SENTINEL"`, the copy failed (editor not focused or selection failed) — report MISMATCH. Only report VERIFIED if clipboard equals expected text AND differs from sentinel.

**Controller:** `safe_gui_ctl.py verify <app-key> <expected...>` handles this automatically.

## Clear Command

To clear editor content before typing: `safe_gui_ctl.py clear <app-key>` sends Ctrl+A then Delete. This prevents stale text from previous sessions contaminating new input.

## Updated Composite Test Workflow

1. Close app (expect `NOT_RUNNING` or `CLOSED`)
2. Launch app (expect `LAUNCHED`, `FOCUSED=true`)
3. Clear editor (expect `CLEARED`)
4. Type text via clipboard (expect `TYPED`, `CLICKED=true`, `CLIPBOARD_SET=True`)
5. Verify text readback (expect `VERIFIED`, `MATCH=true`, READ != sentinel)
6. Close app (expect `CLOSED`)

Controller commands: `list`, `status`, `launch`, `close`, `test`, `type`, `verify`, `clear`.


## Operator Playbook Pointer

قبل أي مهمة واجهة على ويندوز، اقرأ C:/agent-work/rules/OPERATOR_PLAYBOOK.md وطبّقه كاملا. هو المرجع الحاكم لكل عمليات الفتح والإغلاق والكتابة والتحقق. لا ترتجل طرق إدخال أو تحقق خارج safe_gui_ctl.py.
