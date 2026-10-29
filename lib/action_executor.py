from lib.mouse_controller import MouseController
from lib.element_locator import ElementLocator, connect_to_process, start_and_connect
from lib.vision_layer import VisionLayer
import subprocess
import time
import os

class ActionExecutor:
    """منفذ الإجراءات العام — واجهة موحدة لأي تطبيق"""
    
    def __init__(self, backend: str = 'uia'):
        self.mouse = MouseController()
        self.locator = ElementLocator(backend)
        self.vision = VisionLayer()
        self.backend = backend
    
    # ===== Window Management =====
    
    def open_app(self, exe_path: str, wait: float = 2) -> subprocess.Popen:
        """فتح تطبيق"""
        proc = subprocess.Popen([exe_path])
        time.sleep(wait)
        return proc
    
    def start_and_connect(self, exe_path: str, wait: float = 2):
        """تشغيل وربط تلقائي"""
        app = start_and_connect(exe_path, self.backend, wait)
        return app
    
    def connect_to_pid(self, pid: int):
        """ربط بعملية موجودة"""
        return connect_to_process(pid, self.backend)
    
    def find_window(self, criteria: dict):
        """إيجاد نافذة"""
        return self.locator.find_window(criteria)
    
    def get_window(self, app, criteria: dict = None):
        """الحصول على نافذة من Application"""
        if criteria:
            return app.window(**criteria)
        return app.top_window()
    
    def close_window(self, window) -> bool:
        """إغلاق نافذة بأمان"""
        for title in ['إغلاق', 'Close', 'Exit', 'خروج']:
            try:
                btn = window.child_window(title=title, control_type='Button')
                if btn.exists():
                    rect = btn.rectangle()
                    cx = (rect.left + rect.right) // 2
                    cy = (rect.top + rect.bottom) // 2
                    self.mouse.click(cx, cy)
                    window.wait_not('exists', timeout=3)
                    return True
            except:
                continue
        return False
    
    def _find_element(self, window, criteria: dict):
        """إيجاد عنصر داخل نافذة باستخدام window.child_window"""
        search_kwargs = {}
        if 'auto_id' in criteria:
            search_kwargs['auto_id'] = criteria['auto_id']
        if 'control_type' in criteria:
            search_kwargs['control_type'] = criteria['control_type']
        if 'title' in criteria:
            search_kwargs['title'] = criteria['title']
        if 'class_name' in criteria:
            search_kwargs['class_name'] = criteria['class_name']
        if 'found_index' in criteria:
            search_kwargs['found_index'] = criteria['found_index']
        
        if not search_kwargs:
            raise ValueError("At least one search criterion required")
        
        return window.child_window(**search_kwargs)
    
    # ===== Element Actions =====
    
    def click_element(self, window, criteria: dict, track_mouse: bool = True) -> dict:
        """نقر عنصر مع تتبع اختياري للماوس"""
        if track_mouse:
            self.mouse.start_tracking()
        
        element = self._find_element(window, criteria)
        rect = element.rectangle()
        cx = (rect.left + rect.right) // 2
        cy = (rect.top + rect.bottom) // 2
        
        self.mouse.click(cx, cy)
        
        if track_mouse:
            return self.mouse.stop_tracking()
        return {}
    
    def double_click_element(self, window, criteria: dict):
        """نقر مزدوج"""
        element = self._find_element(window, criteria)
        rect = element.rectangle()
        cx = (rect.left + rect.right) // 2
        cy = (rect.top + rect.bottom) // 2
        self.mouse.double_click(cx, cy)
    
    def type_text(self, window, criteria: dict, text: str):
        """كتابة نص (لا يحرك الماوس)"""
        element = self._find_element(window, criteria)
        element.set_edit_text(text)
    
    def get_text(self, window, criteria: dict) -> str:
        """قراءة نص من عنصر"""
        element = self._find_element(window, criteria)
        return element.window_text()
    
    def invoke_element(self, window, criteria: dict):
        """استدعاء إجراء (Invoke pattern — لا يحرك الماوس)"""
        element = self._find_element(window, criteria)
        element.invoke()
    
    def set_focus(self, window, criteria: dict):
        """إعطاء التركيز"""
        element = self._find_element(window, criteria)
        element.set_focus()
    
    # ===== High-level Workflows =====
    
    def open_type_click_close(self, 
                               exe_path: str,
                               window_criteria: dict,
                               type_criteria: dict = None,
                               text: str = None,
                               click_criteria: dict = None,
                               track_mouse: bool = True) -> dict:
        """
        سير عمل كامل: فتح -> كتابة -> نقر -> إغلاق
        يرجع إحصائيات الماوس
        """
        proc = self.open_app(exe_path)
        try:
            win = self.find_window({**window_criteria, 'process_id': proc.pid})
            if not win:
                win = self.find_window(window_criteria)
            
            if type_criteria and text:
                self.type_text(win, type_criteria, text)
            
            stats = {}
            if click_criteria:
                stats = self.click_element(win, click_criteria, track_mouse)
            
            self.close_window(win)
            return stats
        finally:
            try:
                proc.kill()
            except:
                pass
    
    # ===== Diagnostics =====
    
    def dump_window_tree(self, window, depth: int = 2):
        """طباعة شجرة العناصر"""
        self.locator.print_tree(window, depth)
    
    def list_windows(self, filter_str: str = None):
        """قائمة النوافذ"""
        for w in self.locator.desktop.windows():
            title = w.window_text()
            if not filter_str or filter_str.lower() in title.lower():
                print(f"Title: '{title}' | Class: '{w.class_name()}' | PID: {w.process_id()}")
