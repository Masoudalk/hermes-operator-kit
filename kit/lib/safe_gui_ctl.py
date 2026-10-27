import sys
import time
import json
from pathlib import Path
sys.path.insert(0, r"C:\agent-work\lib")

from win_app_ops import (all_pids, app_pids, launch_app_windowed, close_app_windows,
    restore_and_focus, set_clipboard_text, get_clipboard_text,
    send_ctrl_v, send_ctrl_a, send_ctrl_c, click_window_center, send_delete)
from safe_gui_launcher import _log_launch

BUILTIN_APPS = {
    "winver": ("WindowsVersion", "C:/Windows/System32/winver.exe", "winver.exe"),
    "charmap": ("CharacterMap", "C:/Windows/System32/charmap.exe", "charmap.exe"),
    "notepad": ("Notepad", "C:/Windows/System32/notepad.exe", "notepad.exe"),
}

CONFIG_PATH = Path(r"C:\agent-work\config\gui_apps.json")


def load_apps():
    apps = dict(BUILTIN_APPS)
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, dict):
                        name = str(v.get("name", k))
                        exe = str(v.get("exe", ""))
                        proc = str(v.get("process", ""))
                        if not proc and exe:
                            proc = Path(exe).name
                        if exe and proc:
                            apps[str(k).lower()] = (name, exe, proc.lower())
        except Exception as exc:
            print("CONFIG_WARN=" + type(exc).__name__)
    return apps


def print_app(key, app):
    print("APP=" + key)
    print("NAME=" + app[0])
    print("EXE=" + app[1])
    print("PROCESS=" + app[2])


def cmd_list():
    print("APPS=" + ",".join(sorted(load_apps().keys())))
    return 0


def cmd_status(args):
    if len(args) != 1:
        print("USAGE=safe_gui_ctl.py status <app-key>")
        return 2
    key = args[0].lower()
    apps = load_apps()
    if key not in apps:
        print("UNKNOWN_APP=" + key)
        print("RESULT=FAIL")
        return 1
    app = apps[key]
    pids = app_pids(app[2])
    print_app(key, app)
    print("RUNNING=" + str(bool(pids)).lower())
    print("PIDS=" + ",".join(map(str, pids)))
    print("RESULT=OK")
    return 0


def cmd_launch(args):
    if len(args) != 1:
        print("USAGE=safe_gui_ctl.py launch <app-key>")
        return 2
    key = args[0].lower()
    apps = load_apps()
    if key not in apps:
        print("UNKNOWN_APP=" + key)
        print("RESULT=FAIL")
        return 1
    name, exe, proc = apps[key]
    print_app(key, apps[key])
    print("PIDS_BEFORE=" + ",".join(map(str, app_pids(proc))))
    ok, pid, code = launch_app_windowed(name, exe, proc, log_func=_log_launch)
    print("LAUNCH_OK=" + str(ok))
    print("PID=" + (str(pid) if pid else ""))
    print("FOCUSED=" + str(code == "LAUNCHED_FOCUSED").lower())
    print("CODE=" + code)
    if ok:
        print("RESULT=LAUNCHED")
        return 0
    if code == "ALREADY_RUNNING":
        print("RESULT=ALREADY_RUNNING")
        return 0
    print("RESULT=FAIL")
    return 1


def cmd_close(args):
    if len(args) != 1:
        print("USAGE=safe_gui_ctl.py close <app-key>")
        return 2
    key = args[0].lower()
    apps = load_apps()
    if key not in apps:
        print("UNKNOWN_APP=" + key)
        print("RESULT=FAIL")
        return 1
    name, exe, proc = apps[key]
    print_app(key, apps[key])
    print("PIDS_BEFORE=" + ",".join(map(str, app_pids(proc))))
    ok, pid, code = close_app_windows(name, proc, log_func=_log_launch)
    print("CLOSE_OK=" + str(ok))
    print("CODE=" + code)
    print("RUNNING=" + str(bool(app_pids(proc))).lower())
    if code == "CLOSED":
        print("RESULT=CLOSED")
        return 0
    if code == "NOT_RUNNING":
        print("RESULT=NOT_RUNNING")
        return 0
    print("RESULT=FAIL")
    return 1


def cmd_test(args):
    if len(args) != 1:
        print("USAGE=safe_gui_ctl.py test <app-key>")
        return 2
    key = args[0].lower()
    apps = load_apps()
    if key not in apps:
        print("UNKNOWN_APP=" + key)
        print("RESULT=FAIL")
        return 1
    name, exe, proc = apps[key]
    print_app(key, apps[key])
    if app_pids(proc):
        pre_ok, pre_pid, pre_code = close_app_windows(name, proc, log_func=_log_launch)
        print("PRECONDITION_CLOSE_OK=" + str(pre_ok))
        if not pre_ok:
            print("RESULT=FAIL")
            return 1
    ok1, pid1, code1 = launch_app_windowed(name, exe, proc, log_func=_log_launch)
    time.sleep(0.5)
    ok2, pid2, code2 = launch_app_windowed(name, exe, proc)
    duplicate_blocked = (ok2 is False and code2 == "ALREADY_RUNNING" and pid2 == pid1)
    close_ok, close_pid, close_code = close_app_windows(name, proc, log_func=_log_launch)
    gone = not app_pids(proc)
    final = app_pids(proc)
    print("LAUNCH_OK=" + str(ok1))
    print("FIRST_PID=" + (str(pid1) if pid1 else ""))
    print("FOCUSED=" + str(code1 == "LAUNCHED_FOCUSED").lower())
    print("DUPLICATE_OK=" + str(ok2))
    print("DUPLICATE_BLOCKED=" + str(duplicate_blocked))
    print("CLOSE_OK=" + str(close_ok))
    print("GONE=" + str(gone))
    print("FINAL_PIDS=" + ",".join(map(str, final)))
    if ok1 and duplicate_blocked and close_ok and gone and not final:
        print("RESULT=PASS")
        return 0
    print("RESULT=FAIL")
    return 1


def cmd_type(args):
    if len(args) < 2:
        print("USAGE=safe_gui_ctl.py type <app-key> <text...>")
        return 2
    key = args[0].lower()
    text = " ".join(args[1:])
    apps = load_apps()
    if key not in apps:
        print("UNKNOWN_APP=" + key)
        print("RESULT=FAIL")
        return 1
    name, exe, proc = apps[key]
    pids = app_pids(proc)
    if not pids:
        print("RUNNING=false")
        print("RESULT=NOT_RUNNING")
        return 1
    focused = restore_and_focus(pids[0])
    time.sleep(0.2)
    clicked = click_window_center(pids[0], 0.6)
    time.sleep(0.2)
    ok_cb = set_clipboard_text(text)
    send_ctrl_v()
    time.sleep(0.3)
    print("FOCUSED=" + str(focused).lower())
    print("CLICKED=" + str(clicked).lower())
    print("CLIPBOARD_SET=" + str(ok_cb))
    if ok_cb:
        print("RESULT=TYPED")
        return 0
    print("RESULT=FAIL")
    return 1


def cmd_verify(args):
    if len(args) < 2:
        print("USAGE=safe_gui_ctl.py verify <app-key> <expected...>")
        return 2
    key = args[0].lower()
    expected = " ".join(args[1:])
    apps = load_apps()
    if key not in apps:
        print("UNKNOWN_APP=" + key)
        print("RESULT=FAIL")
        return 1
    proc = apps[key][2]
    pids = app_pids(proc)
    if not pids:
        print("RUNNING=false")
        print("RESULT=NOT_RUNNING")
        return 1
    set_clipboard_text("VERIFY_SENTINEL")
    time.sleep(0.1)
    restore_and_focus(pids[0])
    time.sleep(0.2)
    click_window_center(pids[0], 0.6)
    time.sleep(0.2)
    send_ctrl_a()
    send_ctrl_c()
    time.sleep(0.3)
    got = get_clipboard_text()
    print("READ=" + str(got))
    print("MATCH=" + str(got == expected).lower())
    if got == expected:
        print("RESULT=VERIFIED")
        return 0
    print("RESULT=MISMATCH")
    return 1


def cmd_clear(args):
    if len(args) != 1:
        print("USAGE=safe_gui_ctl.py clear <app-key>")
        return 2
    key = args[0].lower()
    apps = load_apps()
    if key not in apps:
        print("UNKNOWN_APP=" + key)
        print("RESULT=FAIL")
        return 1
    proc = apps[key][2]
    pids = app_pids(proc)
    if not pids:
        print("RUNNING=false")
        print("RESULT=NOT_RUNNING")
        return 1
    restore_and_focus(pids[0])
    time.sleep(0.2)
    click_window_center(pids[0], 0.6)
    time.sleep(0.2)
    send_ctrl_a()
    send_delete()
    time.sleep(0.2)
    print("RESULT=CLEARED")
    return 0


def main():
    if len(sys.argv) < 2:
        print("USAGE=safe_gui_ctl.py list|status|launch|close|test <app-key>")
        return 2
    cmd = sys.argv[1].lower()
    args = sys.argv[2:]
    if cmd == "list":
        return cmd_list()
    if cmd == "status":
        return cmd_status(args)
    if cmd == "launch":
        return cmd_launch(args)
    if cmd == "close":
        return cmd_close(args)
    if cmd == "test":
        return cmd_test(args)
    if cmd == "type":
        return cmd_type(args)
    if cmd == "verify":
        return cmd_verify(args)
    if cmd == "clear":
        return cmd_clear(args)
    print("UNKNOWN_COMMAND=" + cmd)
    return 2


if __name__ == "__main__":
    sys.exit(main())
