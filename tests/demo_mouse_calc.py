import time
import ctypes
from pywinauto import Application, Desktop
import subprocess

print("=== عرض تفاعلي: تحريك الماوس وفتح/إغلاق Calculator (الحاسبة) ===")

def get_cursor_pos():
    cursor = ctypes.wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(cursor))
    return (cursor.x, cursor.y)

def move_mouse_to(x, y, duration=1.0):
    """تحريك الماوس بسلاسة إلى إحداثيات محددة"""
    start = get_cursor_pos()
    steps = int(duration * 60)  # 60 FPS
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

print("2. فتح Calculator عبر Application().start()...")
app = Application(backend='uia').start('calc.exe')
time.sleep(3)

print("3. الحصول على النافذة الرئيسية...")
win = app.top_window()
print(f"   النافذة: '{win.window_text()}' | Class: '{win.class_name()}'")

print("4. تحريك الماوس فوق زر الإغلاق (X)...")
close_btn = win.child_window(title='Close', control_type='Button')
if not close_btn.exists():
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
    print("   ✅ Calculator أُغلق بنجاح")
except:
    print("   ⚠️ قد لا يزال مفتوحاً")

print("7. تحريك الماوس للزاوية السفلية اليمنى...")
move_mouse_to(1800, 1000, 1.0)
print(f"   موضع النهائي: {get_cursor_pos()}")

print("\n=== انتهى العرض ===")
