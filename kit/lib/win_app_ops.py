import time
import subprocess
import ctypes
from ctypes import wintypes
import psutil

user32 = ctypes.windll.user32
SW_RESTORE = 9
VK_MENU = 0x12
KEYEVENTF_KEYUP = 0x0002
WM_CLOSE = 0x0010


def all_pids(process_name):
    target = process_name.lower()
    out = []
    for p in psutil.process_iter(["pid", "name"]):
        try:
            n = p.info["name"]
            if n and n.lower() == target:
                out.append(p.info["pid"])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return out


def toplevel_windows(pid):
    out = []
    Proc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def cb(hwnd, lparam):
        wp = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wp))
        if wp.value == pid:
            out.append((hwnd, bool(user32.IsWindowVisible(hwnd)), bool(user32.IsIconic(hwnd))))
        return True

    user32.EnumWindows(Proc(cb), pid)
    return out


def app_pids(process_name):
    return [pid for pid in all_pids(process_name) if toplevel_windows(pid)]


def restore_and_focus(pid):
    import ctypes
    kernel32 = ctypes.windll.kernel32
    wins = toplevel_windows(pid)
    if not wins:
        return False
    for hwnd, visible, iconic in wins:
        if iconic or not visible:
            user32.ShowWindow(hwnd, SW_RESTORE)
    target = wins[0][0]
    focused = False
    fg = user32.GetForegroundWindow()
    if fg:
        fg_thread = user32.GetWindowThreadProcessId(fg, None)
        cur_thread = kernel32.GetCurrentThreadId()
        if fg_thread and fg_thread != cur_thread:
            user32.AttachThreadInput(cur_thread, fg_thread, True)
            focused = bool(user32.SetForegroundWindow(target))
            user32.AttachThreadInput(cur_thread, fg_thread, False)
        else:
            focused = bool(user32.SetForegroundWindow(target))
    else:
        focused = bool(user32.SetForegroundWindow(target))
    if not focused:
        user32.keybd_event(VK_MENU, 0, 0, 0)
        focused = bool(user32.SetForegroundWindow(target))
        user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
    return focused


def wait_for_windowed_pid(process_name, before_all, launched_pid, timeout=10.0):
    start = time.time()
    while time.time() - start < timeout:
        now = set(all_pids(process_name))
        candidates = (now - set(before_all)) | {launched_pid}
        for pid in candidates:
            if toplevel_windows(pid):
                return pid
        time.sleep(0.25)
    return None


def launch_app_windowed(app_name, exe, process_name, log_func=None):
    before = all_pids(process_name)
    windowed_before = [pid for pid in before if toplevel_windows(pid)]
    if windowed_before:
        return False, windowed_before[0], "ALREADY_RUNNING"
    proc = subprocess.Popen([exe])
    pid = wait_for_windowed_pid(process_name, before, proc.pid, timeout=10.0)
    if pid is None:
        return False, None, "NO_WINDOW"
    focused = restore_and_focus(pid)
    if log_func:
        log_func(app_name, pid, exe)
    return True, pid, ("LAUNCHED_FOCUSED" if focused else "LAUNCHED")


def close_app_windows(app_name, process_name, timeout=8.0, log_func=None):
    pids = app_pids(process_name)
    if not pids:
        return False, None, "NOT_RUNNING"
    posted = 0
    for pid in pids:
        for hwnd, visible, iconic in toplevel_windows(pid):
            if visible and user32.PostMessageW(hwnd, WM_CLOSE, 0, 0):
                posted += 1
    if posted == 0:
        return False, pids[0], "NO_VISIBLE_WINDOW"
    start = time.time()
    while time.time() - start < timeout:
        if not app_pids(process_name):
            if log_func:
                log_func(app_name + " CLOSED", pids[0], "win_app_ops.close")
            return True, pids[0], "CLOSED"
        time.sleep(0.25)
    return False, pids[0], "STILL_OPEN"


def set_clipboard_text(text):
    import ctypes
    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002
    kernel32 = ctypes.windll.kernel32
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    user32.SetClipboardData.restype = ctypes.c_void_p
    user32.OpenClipboard.argtypes = [ctypes.c_void_p]
    user32.OpenClipboard.restype = ctypes.c_bool
    if not user32.OpenClipboard(0):
        return False
    user32.EmptyClipboard()
    data = text.encode("utf-16-le") + b"\x00\x00"
    h = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
    if not h:
        user32.CloseClipboard()
        return False
    p = kernel32.GlobalLock(h)
    if not p:
        user32.CloseClipboard()
        return False
    ctypes.memmove(p, data, len(data))
    kernel32.GlobalUnlock(h)
    ok = bool(user32.SetClipboardData(CF_UNICODETEXT, h))
    user32.CloseClipboard()
    return ok


def get_clipboard_text():
    import ctypes
    CF_UNICODETEXT = 13
    user32.OpenClipboard.argtypes = [ctypes.c_void_p]
    user32.OpenClipboard.restype = ctypes.c_bool
    user32.GetClipboardData.argtypes = [ctypes.c_uint]
    user32.GetClipboardData.restype = ctypes.c_void_p
    kernel32 = ctypes.windll.kernel32
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    if not user32.OpenClipboard(0):
        return None
    h = user32.GetClipboardData(CF_UNICODETEXT)
    text = None
    if h:
        p = ctypes.windll.kernel32.GlobalLock(h)
        if p:
            text = ctypes.wstring_at(p)
            ctypes.windll.kernel32.GlobalUnlock(h)
    user32.CloseClipboard()
    return text


def _send_combo(vk):
    VK_CONTROL = 0x11
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    user32.keybd_event(vk, 0, 0, 0)
    user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.15)


def send_ctrl_v():
    _send_combo(0x56)


def send_ctrl_a():
    _send_combo(0x41)


def send_ctrl_c():
    _send_combo(0x43)


def real_click(x, y):
    MOUSEEVENTF_MOVE = 0x0001
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    MOUSEEVENTF_ABSOLUTE = 0x8000
    user32.GetSystemMetrics.argtypes = [ctypes.c_int]
    user32.GetSystemMetrics.restype = ctypes.c_int
    user32.mouse_event.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_ulong]
    sm_cx = user32.GetSystemMetrics(0)
    sm_cy = user32.GetSystemMetrics(1)
    nx = int(x * 65535 / max(1, sm_cx))
    ny = int(y * 65535 / max(1, sm_cy))
    user32.mouse_event(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, nx, ny, 0, 0)
    time.sleep(0.05)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.05)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.1)


def click_window_center(pid, frac_y=0.6):
    import ctypes
    from ctypes import wintypes
    wins = toplevel_windows(pid)
    if not wins:
        return False
    hwnd = wins[0][0]
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    x = (rect.left + rect.right) // 2
    y = rect.top + int((rect.bottom - rect.top) * frac_y)
    real_click(x, y)
    return True


def send_delete():
    VK_DELETE = 0x2E
    user32.keybd_event(VK_DELETE, 0, 0, 0)
    user32.keybd_event(VK_DELETE, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.15)
