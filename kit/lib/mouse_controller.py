import time
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MOVE = 0x0001

class MouseController:
    """تحكم ذكي بالماوس مع تتبع الانحراف"""
    
    def __init__(self):
        self.positions = []
        self.start_pos = None
        self.tracking = False
    
    def get_pos(self) -> tuple:
        """قراءة الموضع الحالي (x, y)"""
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        return (pt.x, pt.y)
    
    def move_to(self, x: int, y: int, duration: float = 0.5, easing: str = 'smoothstep'):
        """تحريك سلس إلى إحداثيات مطلقة"""
        start = self.get_pos()
        steps = max(1, int(duration * 60))
        for i in range(steps + 1):
            t = i / steps
            if easing == 'smoothstep':
                ease = t * t * (3 - 2 * t)
            elif easing == 'ease_out':
                ease = 1 - (1 - t) ** 3
            else:
                ease = t
            cx = int(start[0] + (x - start[0]) * ease)
            cy = int(start[1] + (y - start[1]) * ease)
            user32.SetCursorPos(cx, cy)
            time.sleep(1/60)
        if self.tracking:
            self._record_pos(x, y)
    
    def click(self, x: int = None, y: int = None, button: str = 'left', track: bool = True):
        """نقر في الموضع الحالي أو المحدد"""
        if track and not self.tracking:
            self.start_tracking()
        
        if x is not None and y is not None:
            self.move_to(x, y, duration=0.15)
        
        if button == 'left':
            user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.015)
            user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        elif button == 'right':
            user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            time.sleep(0.015)
            user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
        
        if track:
            self._record_pos(*self.get_pos())
    
    def double_click(self, x: int = None, y: int = None):
        """نقر مزدوج"""
        self.click(x, y)
        time.sleep(0.05)
        self.click(x, y)
    
    def start_tracking(self):
        """بدء تتبع موضع الماوس"""
        self.start_pos = self.get_pos()
        self.positions = [self.start_pos]
        self.tracking = True
    
    def stop_tracking(self) -> dict:
        """إيقاف التتبع وإرجاع الإحصائيات"""
        self.tracking = False
        return self.get_deviation_stats()
    
    def _record_pos(self, x, y):
        if self.tracking:
            self.positions.append((x, y))
    
    def get_deviation_stats(self) -> dict:
        """إحصائيات الانحراف عن الموضع الأولي"""
        if not self.start_pos or not self.positions:
            return {'max': 0, 'avg': 0, 'final': self.get_pos(), 'start': None}
        
        deviations = [
            abs(p[0] - self.start_pos[0]) + abs(p[1] - self.start_pos[1])
            for p in self.positions
        ]
        return {
            'max': max(deviations) if deviations else 0,
            'avg': sum(deviations) / len(deviations) if deviations else 0,
            'final': self.get_pos(),
            'start': self.start_pos,
            'samples': len(self.positions)
        }
    
    def __enter__(self):
        self.start_tracking()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.stop_tracking()