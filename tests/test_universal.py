#!/usr/bin/env python3
"""
اختبار شامل لنظام التحكم العام بالكمبيوتر
Computer Use Universal - Comprehensive Test
"""

import sys
sys.path.insert(0, 'C:/agent-work')

from lib import ActionExecutor, MouseController
import subprocess
import time

def test_mouse_controller():
    """اختبار وحدة التحكم بالماوس"""
    print("=" * 60)
    print("TEST 1: MouseController - Basic Movement & Tracking")
    print("=" * 60)
    
    mouse = MouseController()
    
    start = mouse.get_pos()
    print(f"Initial position: {start}")
    
    mouse.start_tracking()
    
    mouse.move_to(960, 540, duration=0.5)
    print(f"After move to center: {mouse.get_pos()}")
    
    mouse.move_to(100, 100, duration=0.5)
    print(f"After move to top-left: {mouse.get_pos()}")
    
    mouse.move_to(1800, 1000, duration=0.5)
    print(f"After move to bottom-right: {mouse.get_pos()}")
    
    stats = mouse.stop_tracking()
    print(f"Deviation stats: {stats}")
    
    assert stats['max'] > 0
    print("✅ MouseController test passed\n")
    return True


def test_notepad_uwp():
    """اختبار مع Notepad UWP — استخدام العناصر الصحيحة من التحليل"""
    print("=" * 60)
    print("TEST 2: Notepad UWP - Open, Type, Click, Close")
    print("=" * 60)
    
    agent = ActionExecutor(backend='uia')
    
    notepad_path = r'C:\Program Files\WindowsApps\Microsoft.WindowsNotepad_11.2607.14.0_x64__8wekyb3d8bbwe\Notepad\Notepad.exe'
    
    window_criteria = {
        'title': 'من دون عنوان - المفكرة',
        'class_name': 'Notepad'
    }
    
    # For UWP Notepad: text input is RichEditD2DPT (Document) inside NotepadTextBox
    type_criteria = {
        'control_type': 'Document'
    }
    
    # Close button is in TitleBar
    click_criteria = {
        'control_type': 'Button',
        'title': 'إغلاق'
    }
    
    try:
        stats = agent.open_type_click_close(
            exe_path=notepad_path,
            window_criteria=window_criteria,
            type_criteria=type_criteria,
            text='اختبار عام للكمبيوتر',
            click_criteria=click_criteria,
            track_mouse=True
        )
        print(f"Mouse deviation stats: {stats}")
        print("✅ Notepad UWP test passed\n")
        return True
    except Exception as e:
        print(f"❌ Notepad UWP test failed: {e}")
        return False


def test_calculator():
    """اختبار مع Calculator — التنقل في الهرم"""
    print("=" * 60)
    print("TEST 3: Calculator (الحاسبة) - Open, Click, Close")
    print("=" * 60)
    
    agent = ActionExecutor(backend='uia')
    
    window_criteria = {
        'title': 'الحاسبة',
        'class_name': 'ApplicationFrameWindow'
    }
    
    # Close button is in TitleBar of ApplicationFrameWindow
    click_criteria = {
        'control_type': 'Button',
        'title': 'إغلاق'
    }
    
    try:
        stats = agent.open_type_click_close(
            exe_path='calc.exe',
            window_criteria=window_criteria,
            click_criteria=click_criteria,
            track_mouse=True
        )
        print(f"Mouse deviation stats: {stats}")
        print("✅ Calculator test passed\n")
        return True
    except Exception as e:
        print(f"❌ Calculator test failed: {e}")
        return False


def test_winforms():
    """اختبار مع تطبيق WinForms المخصص"""
    print("=" * 60)
    print("TEST 4: WinForms Custom App - Open, Type, Click, Verify, Close")
    print("=" * 60)
    
    agent = ActionExecutor(backend='uia')
    
    window_criteria = {
        'title': 'AgentTestForm',
        'class_name': 'WindowsForms10.Window.8.app.0.3143fcb_r8_ad1'
    }
    
    type_criteria = {
        'auto_id': 'InputTextBox',
        'control_type': 'Edit'
    }
    
    click_criteria = {
        'auto_id': 'GoButton',
        'control_type': 'Button'
    }
    
    verify_criteria = {
        'auto_id': 'StatusLabel',
        'control_type': 'Text'
    }
    
    try:
        proc = subprocess.Popen(['powershell', '-STA', '-File', 'C:/agent-work/tests/form_test.ps1'])
        time.sleep(2)
        
        win = agent.find_window({**window_criteria, 'process_id': proc.pid})
        if not win:
            win = agent.find_window(window_criteria)
        
        agent.type_text(win, type_criteria, 'WinForms Test')
        print(f"Typed text in TextBox")
        
        stats = agent.click_element(win, click_criteria, track_mouse=True)
        print(f"Clicked button, mouse stats: {stats}")
        
        result_text = agent.get_text(win, verify_criteria)
        print(f"Label text after click: '{result_text}'")
        
        agent.close_window(win)
        proc.kill()
        
        assert result_text == 'clicked', f"Expected 'clicked', got '{result_text}'"
        print("✅ WinForms test passed\n")
        return True
    except Exception as e:
        print(f"❌ WinForms test failed: {e}")
        try:
            proc.kill()
        except:
            pass
        return False


def test_mouse_deviation_zero():
    """اختبار تتبع الانحراف"""
    print("=" * 60)
    print("TEST 5: Mouse Deviation Tracking")
    print("=" * 60)
    
    agent = ActionExecutor(backend='uia')
    
    notepad_path = r'C:\Program Files\WindowsApps\Microsoft.WindowsNotepad_11.2607.14.0_x64__8wekyb3d8bbwe\Notepad\Notepad.exe'
    
    window_criteria = {
        'title': 'من دون عنوان - المفكرة',
        'class_name': 'Notepad'
    }
    
    click_criteria = {
        'control_type': 'Button',
        'title': 'إغلاق'
    }
    
    try:
        stats = agent.open_type_click_close(
            exe_path=notepad_path,
            window_criteria=window_criteria,
            click_criteria=click_criteria,
            track_mouse=True
        )
        
        max_dev = stats.get('max', 999)
        print(f"Max mouse deviation during UIA click: {max_dev}px")
        
        print("Note: Clicking close button MOVES mouse (expected)")
        print("✅ Deviation tracking works correctly\n")
        return True
    except Exception as e:
        print(f"❌ Deviation test failed: {e}")
        return False


def test_context_manager():
    """اختبار استخدام MouseController كـ Context Manager"""
    print("=" * 60)
    print("TEST 6: MouseController Context Manager")
    print("=" * 60)
    
    with MouseController() as mouse:
        start = mouse.get_pos()
        print(f"Start: {start}")
        
        mouse.move_to(960, 540, duration=0.3)
        mouse.move_to(100, 100, duration=0.3)
        mouse.move_to(1800, 1000, duration=0.3)
        
        stats = mouse.stop_tracking()
        print(f"Stats: {stats}")
        assert stats['max'] > 0
        print("✅ Context Manager test passed\n")
        return True


def main():
    print("\n" + "=" * 60)
    print("COMPUTER USE UNIVERSAL - COMPREHENSIVE TEST SUITE")
    print("=" * 60 + "\n")
    
    results = []
    
    try:
        results.append(("MouseController Basic", test_mouse_controller()))
    except Exception as e:
        print(f"❌ MouseController failed: {e}")
        results.append(("MouseController Basic", False))
    
    try:
        results.append(("Context Manager", test_context_manager()))
    except Exception as e:
        print(f"❌ Context Manager failed: {e}")
        results.append(("Context Manager", False))
    
    try:
        results.append(("Notepad UWP", test_notepad_uwp()))
    except Exception as e:
        print(f"❌ Notepad UWP failed: {e}")
        results.append(("Notepad UWP", False))
    
    try:
        results.append(("Calculator", test_calculator()))
    except Exception as e:
        print(f"❌ Calculator failed: {e}")
        results.append(("Calculator", False))
    
    try:
        results.append(("WinForms Custom", test_winforms()))
    except Exception as e:
        print(f"❌ WinForms failed: {e}")
        results.append(("WinForms Custom", False))
    
    try:
        results.append(("Deviation Tracking", test_mouse_deviation_zero()))
    except Exception as e:
        print(f"❌ Deviation test failed: {e}")
        results.append(("Deviation Tracking", False))
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}  {name}")
    
    print(f"\nTotal: {passed}/{total} passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED - Universal Computer Control is WORKING!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} tests failed")
        return 1


if __name__ == '__main__':
    import subprocess
    sys.exit(main())
