import subprocess, time, sys, ctypes
from ctypes import wintypes
import psutil

EXE = r"C:\Windows\System32\notepad.exe"

def pids_for(name):
    out = []
    for p in psutil.process_iter(["pid", "name"]):
        try:
            n = p.info["name"]
            if n and n.lower() == name.lower():
                out.append(p.info["pid"])
        except Exception:
            pass
    return out

def windows_for(pid):
    user32 = ctypes.windll.user32
    found = []
    Proc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, lparam):
        wp = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wp))
        if wp.value == lparam:
            found.append((hwnd, bool(user32.IsWindowVisible(hwnd))))
        return True
    user32.EnumWindows(Proc(cb), pid)
    return found

print("BEFORE_PIDS", pids_for("notepad.exe"))

proc = subprocess.Popen([EXE])
print("STUB_PID", proc.pid)

for step in range(6):
    time.sleep(0.5)
    alive = psutil.pid_exists(proc.pid)
    try:
        status = psutil.Process(proc.pid).status()
    except Exception as e:
        status = "GONE:" + type(e).__name__
    print("T+%.1fs STUB_ALIVE=%s STATUS=%s NOTEPAD_PIDS=%s" % (0.5 * (step + 1), alive, status, pids_for("notepad.exe")))

time.sleep(2)
pids = pids_for("notepad.exe")
print("FINAL_NOTEPAD_PIDS", pids)

for pid in pids:
    print("WINDOWS_FOR", pid, windows_for(pid))
    try:
        print("PROC_EXE", pid, psutil.Process(pid).exe())
    except Exception as e:
        print("PROC_EXE_ERR", pid, type(e).name)

if pids:
    sys.path.insert(0, r"C:\agent-work\lib")
    from safe_gui_launcher import close_app_safely
    print("CLEANUP", close_app_safely("Notepad", "notepad.exe"))
else:
    print("CLEANUP_NOTHING_TO_CLOSE")
