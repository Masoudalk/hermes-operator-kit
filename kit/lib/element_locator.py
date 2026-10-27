from pywinauto import Desktop, Application
from pywinauto.findwindows import ElementNotFoundError
import subprocess
import time

class ElementLocator:
    """محدد العناصر متعدد الاستراتيجيات — UIA, Win32, Visual"""
    
    def __init__(self, backend: str = 'uia'):
        self.backend = backend
        self.desktop = Desktop(backend=backend)
    
    def find_window(self, criteria: dict):
        """
        إيجاد نافذة بالمعايير — يرجع WindowSpecification دائماً:
        - title: عنوان النافذة
        - class_name: اسم الفئة
        - process_id: معرف العملية
        - process_name: اسم العملية
        - path: مسار التنفيذ
        - auto_id: معرف الأتمتة
        """
        # Strategy 1: by process_id (الأكثر دقة)
        if 'process_id' in criteria:
            try:
                app = Application(backend=self.backend).connect(process=criteria['process_id'])
                return app.top_window()
            except:
                pass
        
        # Strategy 2: by path
        if 'path' in criteria:
            try:
                app = Application(backend=self.backend).connect(path=criteria['path'])
                return app.top_window()
            except:
                pass
        
        # Strategy 3: by title + class — connect via Application
        for w in self.desktop.windows():
            match = True
            if 'title' in criteria and criteria['title'] not in w.window_text():
                match = False
            if 'class_name' in criteria and criteria['class_name'] != w.class_name():
                match = False
            if 'process_name' in criteria:
                try:
                    import psutil
                    p = psutil.Process(w.process_id())
                    if criteria['process_name'].lower() not in p.name().lower():
                        match = False
                except:
                    match = False
            if match:
                # Connect via Application to get WindowSpecification
                try:
                    app = Application(backend=self.backend).connect(handle=w.handle)
                    return app.window(handle=w.handle)
                except:
                    # Fallback: return the raw wrapper but wrap it
                    return w
        return None
    
    def find_element(self, window, criteria: dict):
        """
        إيجاد عنصر داخل نافذة:
        - auto_id: معرف الأتمتة (الأفضل)
        - control_type: نوع التحكم (Button, Edit, Text, etc.)
        - title: نص العنصر
        - class_name: اسم الفئة
        - found_index: الفهرس إذا تكرر
        """
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
    
    def find_by_visual(self, window, description: str) -> tuple:
        """إيجاد عنصر بالرؤية (يتطلب VisionLayer خارجي)"""
        raise NotImplementedError("Use VisionLayer.find_element_coords externally")
    
    def print_tree(self, window, depth: int = 2):
        """طباعة شجرة العناصر للتشخيص"""
        window.print_control_identifiers(depth=depth)

def connect_to_process(pid: int, backend: str = 'uia'):
    """اختصار للربط بعملية"""
    return Application(backend=backend).connect(process=pid)

def start_and_connect(exe_path: str, backend: str = 'uia', wait: float = 2):
    """تشغيل وربط تلقائي"""
    app = Application(backend=backend).start(exe_path)
    time.sleep(wait)
    return app
