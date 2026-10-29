import time
import ctypes
from pywinauto import Application, Desktop
import subprocess
import psutil

print("=== اختبار Calculator تحت قاطع فتح النوافذ (قسم 9) ===")

def get_cursor_pos():
    cursor = ctypes.wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(cursor))
    return (cursor.x, cursor.y)

# 1. Get-Process قبل الفتح - باستخدام psutil للعملية الفعلية
print("1. Get-Process قبل الفتح (psutil):")
calc_pids_before = set()
for p in psutil.process_iter(['pid', 'name']):
    name = p.info['name'].lower()
    if 'calculator' in name or 'calc' in name or '\u062d\u0627\u0633\u0628\u0629' in name:
        calc_pids_before.add(p.info['pid'])
        print(f"   PID موجود: {p.info['pid']} ({p.info['name']})")

# Also get window handles before
calc_handles_before = set()
desktop = Desktop(backend='uia')
for w in desktop.windows():
    title = w.window_text()
    if '\u0627\u0644\u062d\u0627\u0633\u0628\u0629' in title or 'Calculator' in title:
        calc_handles_before.add(w.handle)

print(f"   Handles قبل: {calc_handles_before}")

# 2. فتح Calculator
print("\n2. فتح Calculator...")
proc = subprocess.Popen(['calc.exe'])
time.sleep(3)

# 3. Get-Process بعد الفتح - إيجاد PID الجديد والنافذة الجديدة
print("3. Get-Process بعد الفتح - إيجاد العملية والنافذة الجديدة:")

calc_pids_after = set()
for p in psutil.process_iter(['pid', 'name']):
    name = p.info['name'].lower()
    if 'calculator' in name or 'calc' in name or '\u062d\u0627\u0633\u0628\u0629' in name:
        calc_pids_after.add(p.info['pid'])

new_pids = calc_pids_after - calc_pids_before
print(f"   PIDs قبل: {calc_pids_before}")
print(f"   PIDs بعد: {calc_pids_after}")
print(f"   PIDs جديدة: {new_pids}")

# Get window handles after
calc_handles_after = set()
for w in desktop.windows():
    title = w.window_text()
    if '\u0627\u0644\u062d\u0627\u0633\u0628\u0629' in title or 'Calculator' in title:
        calc_handles_after.add(w.handle)

new_handles = calc_handles_after - calc_handles_before
print(f"   Handles قبل: {calc_handles_before}")
print(f"   Handles بعد: {calc_handles_after}")
print(f"   Handles جديدة: {new_handles}")

if not new_pids and not new_handles:
    print("   ❌ فشل: لم يتم اكتشاف عملية أو نافذة جديدة")
    proc.kill()
    exit(1)

# Use the new handle if available, otherwise find by new PID
target_handle = None
target_pid = None

if new_handles:
    target_handle = list(new_handles)[0]
    # Find PID for this handle
    for w in desktop.windows():
        if w.handle == target_handle:
            target_pid = w.process_id()
            break
elif new_pids:
    target_pid = list(new_pids)[0]
    # Find handle for this PID
    for w in desktop.windows():
        if w.process_id() == target_pid:
            target_handle = w.handle
            break

if not target_handle or not target_pid:
    print("   ❌ فشل: لا يمكن تحديد الهدف")
    proc.kill()
    exit(1)

print(f"   ✅ الهدف: PID={target_pid} (Handle: {target_handle})")

# 4. ربط النافذة بالـ Handle
print(f"\n4. ربط النافذة بـ Handle={target_handle}...")
try:
    app = Application(backend='uia').connect(handle=target_handle, timeout=10)
    win = app.window(handle=target_handle)
    print(f"   ✅ متصل: '{win.window_text()}' (Class: {win.class_name()})")
except Exception as e:
    print(f"   ❌ فشل الاتصال: {e}")
    proc.kill()
    exit(1)

# 5. تتبع الماوس
print("\n5. بدء تتبع الماوس...")
start_pos = get_cursor_pos()
max_dev = 0
positions = []
tracking = True

def track_cursor():
    global max_dev
    while tracking:
        pos = get_cursor_pos()
        positions.append((time.time(), pos))
        if positions and len(positions) > 1:
            dev = abs(pos[0] - start_pos[0]) + abs(pos[1] - start_pos[1])
            if dev > max_dev:
                max_dev = dev
        time.sleep(0.1)

import threading
tracker_thread = threading.Thread(target=track_cursor, daemon=True)
tracker_thread.start()

# 6. تحريك الماوس لمنتصف الشاشة
print("6. تحريك الماوس لمنتصف الشاشة (960, 540)...")
ctypes.windll.user32.SetCursorPos(960, 540)
time.sleep(0.5)

# 7. تحريك الماوس للزاوية السفلية اليمنى
print("7. تحريك الماوس للزاوية السفلية اليمنى (1800, 1000)...")
ctypes.windll.user32.SetCursorPos(1800, 1000)
time.sleep(0.5)

# 8. المحاولة الأولى: إرسال WM_CLOSE عبر PostMessage للـ Handle
print("\n8. المحاولة الأولى: إغلاق Calculator بـ PostMessage WM_CLOSE...")
success = False

try:
    print("   إرسال WM_CLOSE (0x0010) للـ Handle...")
    ctypes.windll.user32.PostMessageW(target_handle, 0x0010, 0, 0)  # WM_CLOSE = 0x0010
    time.sleep(1.5)
    
    # التحقق من الإغلاق
    try:
        # Need to check via desktop since win object may be stale
        for w in desktop.windows():
            if w.handle == target_handle:
                print("   ❌ النافذة لا تزال موجودة بعد المحاولة الأولى")
                success = False
                break
        else:
            print("   ✅ نجح الإغلاق في المحاولة الأولى (PostMessage WM_CLOSE)")
            success = True
    except:
        print("   ❌ خطأ في التحقق من الإغلاق")
        success = False
except Exception as e:
    print(f"   ❌ خطأ في المحاولة الأولى: {e}")
    success = False

# 9. المحاولة الثانية إذا فشلت الأولى - إرسال WM_CLOSE مرة أخرى
if not success:
    print("\n9. المحاولة الثانية: إرسال WM_CLOSE مرة أخرى...")
    try:
        ctypes.windll.user32.PostMessageW(target_handle, 0x0010, 0, 0)
        time.sleep(1.5)
        
        # التحقق من الإغلاق
        try:
            for w in desktop.windows():
                if w.handle == target_handle:
                    print("   ❌ النافذة لا تزال موجودة بعد المحاولة الثانية")
                    success = False
                    break
            else:
                print("   ✅ نجح الإغلاق في المحاولة الثانية (PostMessage WM_CLOSE)")
                success = True
        except:
            print("   ❌ خطأ في التحقق من الإغلاق")
            success = False
    except Exception as e:
        print(f"   ❌ خطأ في المحاولة الثانية: {e}")
        success = False

# 10. إيقاف التتبع
tracking = False
time.sleep(0.2)
end_pos = get_cursor_pos()

# 11. إذا فشلت المحاولتان: توقف فوري، أغلق بـ Taskkill
if not success:
    print("\n❌ فشلت المحاولتان — توقف فوري، إغلاق بـ Taskkill...")
    try:
        subprocess.run(['taskkill', '/F', '/PID', str(target_pid)], capture_output=True, text=True)
        print(f"   Taskkill executed for PID {target_pid}")
    except Exception as e:
        print(f"   خطأ في Taskkill: {e}")

# 12. النتائج
print(f"\n=== نتائج تتبع الماوس ===")
print(f"موضع البداية: {start_pos}")
print(f"موضع النهاية: {end_pos}")
print(f"أقصى انحراف: {max_dev} بكسل")

# تحليل الانحراف أثناء العمليات (استثناء تحريك الماوس اليدوي في الخطوتين 6 و 7)
manual_moves_end = (1800, 1000)
auto_deviation = abs(end_pos[0] - manual_moves_end[0]) + abs(end_pos[1] - manual_moves_end[1])
print(f"انحراف بعد العمليات التلقائية (من 1800,1000): {auto_deviation} بكسل")

print(f"\n=== النتيجة النهائية ===")
if success:
    print("✅ نجح الاختبار: Calculator أُغلق بـ PostMessage WM_CLOSE")
else:
    print("❌ فشل الاختبار: المحاولتان فشلتا، أُغلق بـ Taskkill")

print(f"PID المستهدف: {target_pid}")
print(f"PIDs قبل: {calc_pids_before}")
print(f"PIDs بعد: {calc_pids_after}")
print(f"PID الجديد: {target_pid}")