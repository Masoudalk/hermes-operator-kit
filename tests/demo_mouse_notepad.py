import time
import ctypes
from pywinauto import Application, Desktop
import subprocess

print("=== عرض تفاعلي: تحريك الماوس وفتح/إغلاق Notepad (UWP) ===")

def get_cursor_pos():
    cursor = ctypes.wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(cursor))
    return (cursor.x, cursor.y)

def move_mouse_to(x, y, duration=1.0):
    """تحريك الماوس بسلاسة إلى إحداثيات محددة"""
    start = get_cursor_pos()
    steps = int(duration * 60)
    for i in range(steps + 1):
        t = i / steps
        ease = t * t * (3 - 2 * t)
        cx = int(start[0] + (x - start[0]) * ease)
        cy = int(start[1] + (y - start[1]) * ease)
        ctypes.windll.user32.SetCursorPos(cx, cy)
        time.sleep(1/60)

print("1. تحريك الماوس إلى منتصف الشاشة...")
move_mouse_to(960, 540, 1.5)
print(f"   موضع الماوس الآن: {get_cursor_pos()}")

print("2. تشغيل Notepad UWP (سينشط المثيل الموجود)...")
notepad_path = r'C:\Program Files\WindowsApps\Microsoft.WindowsNotepad_11.2607.14.0_x64__8wekyb3d8bbwe\Notepad\Notepad.exe'
subprocess.Popen([notepad_path])
time.sleep(2)

print("3. الاتصال بالمثيل الموجود لـ Notepad (PID 4528)...")
app = Application(backend='uia').connect(process=4528)
win = app.window(title='من دون عنوان - المفكرة')
win.wait('visible', timeout=10)
print(f"   النافذة متصلة: '{win.window_text()}'")

print("4. تحريك الماوس فوق زر الإغلاق (X)...")
close_btn = win.child_window(title='إغلاق', control_type='Button')
rect = close_btn.rectangle()
center_x = (rect.left + rect.right) // 2
center_y = (rect.top + rect.bottom) // 2

move_mouse_to(center_x, center_y, 1.0)
print(f"   الماوس فوق زر الإغلاق: ({center_x}, {center_y})")

print("5. النقر على زر الإغلاق...")
close_btn.click()
time.sleep(0.5)

print("6. التحقق من الإغلاق...")
try:
    win.wait_not('exists', timeout=3)
    print("   ✅ Notepad أُغلق بنجاح")
except:
    print("   ⚠️ قد لا يزال مفتوحاً")

print("7. تحريك الماوس للزاوية السفلية اليمنى...")
move_mouse_to(1800, 1000, 1.0)
print(f"   موضع النهائي: {get_cursor_pos()}")

print("\n=== انتهى العرض ===")
