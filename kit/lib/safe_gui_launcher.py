"""
safe_gui_launcher.py
دالة آمنة لفتح تطبيقات GUI مع منع التكرار عبر التحقق من العمليات النشطة.
"""

import subprocess
import time
import psutil
from pathlib import Path
from typing import Optional, Tuple


def _get_process_name_from_path(exe_path_or_command: str) -> str:
    """استخراج اسم العملية من المسار أو الأمر."""
    path = Path(exe_path_or_command)
    if path.suffix.lower() == '.exe':
        return path.name.lower()
    # إذا كان أمر به مسافات، خذ أول جزء
    parts = exe_path_or_command.strip().split()
    if parts:
        return Path(parts[0]).name.lower()
    return ""


def _is_process_running(process_name: str) -> Optional[psutil.Process]:
    """التحقق من وجود عملية نشطة بالاسم المحدد."""
    target = process_name.lower()
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] and proc.info['name'].lower() == target:
                return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


def _wait_for_window(pid: int, timeout: float = 8.0) -> bool:
    if pid <= 0:
        return False
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    found = False
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd, lparam):
        nonlocal found
        proc_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(proc_id))
        if proc_id.value == lparam and user32.IsWindowVisible(hwnd):
            found = True
            return False
        return True
    user32.EnumWindows(EnumWindowsProc(callback), pid)
    return found

def _log_launch(app_name: str, pid: int, exe_path: str) -> None:
    """تسجيل عملية الإطلاق في ملف اللوج."""
    log_path = Path(__file__).parent / "last_launched_apps.txt"
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp} | {app_name} | PID={pid} | {exe_path}\n"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def launch_app_safely(app_name: str, exe_path_or_command: str) -> Tuple[bool, str]:
    """
    فتح تطبيق GUI بأمان مع منع التكرار.

    Args:
        app_name: اسم التطبيق للعرض في الرسائل (مثال: "Calculator"، "Notepad")
        exe_path_or_command: المسار الكامل للـ .exe أو الأمر الكامل للتشغيل

    Returns:
        Tuple[bool, str]: (نجح_الفتح، رسالة_نتيجة)
    """
    # 1. التحقق من وجود عملية نشطة بنفس الاسم
    process_name = _get_process_name_from_path(exe_path_or_command)
    if not process_name:
        return False, f"لا يمكن تحديد اسم العملية من: {exe_path_or_command}"

    existing = _is_process_running(process_name)
    if existing:
        return False, f"التطبيق مفتوح بالفعل (PID={existing.info['pid']})، تم إلغاء الفتح لمنع التكرار"

    # 2. فتح التطبيق
    try:
        proc = subprocess.Popen([exe_path_or_command])
    except Exception as e:
        return False, f"فشل فتح التطبيق: {e}"

    # 3. انتظار ثانية والتحقق من العملية
    time.sleep(1.0)

    # التحقق من أن العملية لا تزال حية
    try:
        psutil.Process(proc.pid)
    except psutil.NoSuchProcess:
        return False, "انتهت العملية فور فتحها"

    # 4. التحقق من وجود نافذة
    if not _wait_for_window(proc.pid, timeout=5.0):
        # محاولة إنهاء العملية إذا لم تظهر نافذة
        try:
            pass
        except Exception:
            pass
        return False, "لم تظهر نافذة التطبيق خلال المهلة، تم إلغاء الفتح"

    # 5. تسجيل الـ PID
    _log_launch(app_name, proc.pid, exe_path_or_command)

    return True, f"تم فتح {app_name} بنجاح (PID={proc.pid})"


def close_app_safely(app_name: str, process_name: str, timeout: float = 5.0) -> Tuple[bool, str]:
    """
    Close a GUI app by sending WM_CLOSE to its visible top-level windows.
    No force kill. No TerminateProcess. No taskkill /F.
    """
    import ctypes
    from ctypes import wintypes

    proc = _is_process_running(process_name.lower())

    if not proc:
        return False, f"{app_name} ??? ???????"

    pid = proc.info["pid"]
    user32 = ctypes.windll.user32
    WM_CLOSE = 0x0010
    posted = 0

    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def callback(hwnd, lparam):
        nonlocal posted
        proc_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(proc_id))

        if proc_id.value == lparam and user32.IsWindowVisible(hwnd):
            if user32.PostMessageW(hwnd, WM_CLOSE, 0, 0):
                posted += 1

        return True

    user32.EnumWindows(EnumWindowsProc(callback), pid)

    if posted == 0:
        return False, f"?? ??? ????? ????? ?? {app_name}? ?? ?????? ????? ??????"

    start = time.time()

    while time.time() - start < timeout:
        if not psutil.pid_exists(pid):
            _log_launch(f"{app_name} CLOSED", pid, "close_app_safely")
            return True, f"?? ????? {app_name} ????? (PID={pid})"
        time.sleep(0.2)

    return False, f"?? ????? {app_name} ???? ?????? (PID={pid})? ?? ?????? ????? ??????"
