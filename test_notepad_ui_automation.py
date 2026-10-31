# اختبار المستوى 3: UI Automation بدون تحريك المؤشر
# الهدف: فتح Notepad، كتابة نص بـ type_keys (بدون ماوس)، قياس حركة المؤشر

import time
import ctypes
from ctypes import wintypes
import threading

# قائمة لتسجيل مواضع المؤشر
cursor_positions = []
monitoring = True

def get_cursor_pos():
    """قراءة موضع المؤشر الحالي"""
    pt = wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return (pt.x, pt.y)

def monitor_cursor():
    """مراقبة المؤشر كل 100 ميلي ثانية"""
    global monitoring
    while monitoring:
        pos = get_cursor_pos()
        cursor_positions.append((time.time(), pos))
        time.sleep(0.1)

# بدء المراقبة
initial_pos = get_cursor_pos()
print(f"الموضع الأولي للمؤشر: {initial_pos}")

monitor_thread = threading.Thread(target=monitor_cursor, daemon=True)
monitor_thread.start()

# انتظار 10 ثوانٍ للمستخدم لرفع يده
print("سأبدأ الاختبار بعد 10 ثوانٍ...")
time.sleep(10)

# بدء الاختبار
print("بدء الاختبار الآن...")
test_start_time = time.time()

try:
    from pywinauto import Application
    import subprocess
    
    # فتح Notepad (بدون ماوس)
    process = subprocess.Popen(['notepad.exe'])
    time.sleep(2)  # انتظار فتح النافذة
    
    # الاتصال بـ Notepad عبر PID
    app = Application(backend='uia').connect(process=process.pid)
    
    # الحصول على نافذة Notepad
    notepad_window = app.window(class_name='Notepad')
    notepad_window.set_focus()
    
    # الحصول على عنصر التحرير (Edit control)
    edit_control = notepad_window.child_window(class_name='Edit')
    
    # **استخدام type_keys بدلاً من click**
    # type_keys يكتب النص مباشرة بدون تحريك الماوس
    edit_control.type_keys('Hello from UI Automation test! السلام عليكم', with_spaces=True)
    
    time.sleep(2)
    
    # قراءة النص للتحقق
    text_content = edit_control.window_text()
    print(f"النص المكتوب: {text_content}")
    
    # إغلاق Notepad بدون حفظ
    notepad_window.close()
    time.sleep(0.5)
    
    # النقر على "Don't Save" إن ظهر مربع الحوار
    try:
        # محاولة العثور على نافذة الحوار
        if app.window(title_re='.*Notepad.*').exists(timeout=1):
            dialog = app.window(title_re='.*Notepad.*')
            # استخدام invoke بدلاً من click
            dont_save_btn = dialog.child_window(title="Don't Save", control_type="Button")
            dont_save_btn.invoke()  # invoke لا يحرك الماوس
    except Exception as e:
        print(f"لم يظهر مربع حفظ أو تم إغلاقه: {e}")
    
    test_end_time = time.time()
    test_duration = test_end_time - test_start_time
    
    # إيقاف المراقبة
    monitoring = False
    time.sleep(0.3)
    
    # تحليل حركة المؤشر
    print(f"\n=== نتائج الاختبار ===")
    print(f"مدة الاختبار: {test_duration:.2f} ثانية")
    print(f"عدد القياسات: {len(cursor_positions)}")
    
    # حساب أقصى انحراف
    max_deviation = 0
    for timestamp, pos in cursor_positions:
        if timestamp >= test_start_time:
            deviation = ((pos[0] - initial_pos[0])**2 + (pos[1] - initial_pos[1])**2)**0.5
            if deviation > max_deviation:
                max_deviation = deviation
    
    print(f"الموضع الأولي: {initial_pos}")
    print(f"أقصى انحراف: {max_deviation:.2f} بكسل")
    
    # النتيجة النهائية
    if max_deviation < 5:  # تسامح 5 بكسل (تذبذب طبيعي للنظام)
        print("✅ النتيجة: نجح — المؤشر لم يتحرك")
    else:
        print(f"❌ النتيجة: فشل — المؤشر تحرك بمقدار {max_deviation:.2f} بكسل")
    
    # قياس ذاكرة عملية Notepad (إن كانت لا تزال قائمة)
    try:
        import psutil
        if process.poll() is None:  # العملية لا تزال تعمل
            proc = psutil.Process(process.pid)
            mem_mb = proc.memory_info().rss / (1024 * 1024)
            print(f"ذاكرة Notepad: {mem_mb:.1f} MB")
        else:
            print("Notepad أُغلق بالفعل")
    except Exception as e:
        print(f"لم يمكن قياس الذاكرة: {e}")

except Exception as e:
    monitoring = False
    print(f"❌ خطأ في الاختبار: {e}")
    import traceback
    traceback.print_exc()
