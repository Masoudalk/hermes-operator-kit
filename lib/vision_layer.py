from PIL import ImageGrab, Image
import os
import time

class VisionLayer:
    """طبقة الفهم البصري — التقاط الشاشة وتحليلها"""
    
    def __init__(self):
        self.screen_size = self._get_screen_size()
        self.tmp_dir = 'C:/agent-work/tmp'
        os.makedirs(self.tmp_dir, exist_ok=True)
    
    def _get_screen_size(self) -> tuple:
        import ctypes
        user32 = ctypes.windll.user32
        return (user32.GetSystemMetrics(0), user32.GetSystemMetrics(1))
    
    def capture(self, region: tuple = None) -> Image.Image:
        """
        التقاط الشاشة
        region: (left, top, right, bottom) أو None للشاشة كاملة
        """
        return ImageGrab.grab(bbox=region)
    
    def capture_window(self, window) -> Image.Image:
        """التقاط نافذة محددة"""
        rect = window.rectangle()
        return ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom))
    
    def save_capture(self, image: Image.Image, prefix: str = 'capture') -> str:
        """حفظ اللقطة وإرجاع المسار"""
        timestamp = int(time.time() * 1000)
        path = os.path.join(self.tmp_dir, f'{prefix}_{timestamp}.png')
        image.save(path)
        return path
    
    def analyze(self, image: Image.Image, question: str) -> dict:
        """سؤال نموذج الرؤية (يتطلب vision_analyze tool)"""
        path = self.save_capture(image, 'vision_query')
        return {'image_path': path, 'question': question}
    
    def find_element_coords(self, description: str, region: tuple = None) -> tuple:
        """
        إيجاد إحداثيات عنصر بالوصف الطبيعي
        يرجع: (x, y, confidence) أو None
        """
        image = self.capture(region)
        result = self.analyze(image, 
            f"Find the exact pixel coordinates (x, y) of: {description}. "
            f"Screen size: {self.screen_size}. "
            f"Return ONLY JSON: {{\"x\": int, \"y\": int, \"confidence\": float}}")
        return result
    
    def get_screen_regions(self, grid: tuple = (3, 3)) -> list:
        """تقسيم الشاشة إلى شبكة للأوامر النسبية"""
        w, h = self.screen_size
        cols, rows = grid
        regions = []
        for r in range(rows):
            for c in range(cols):
                left = c * w // cols
                top = r * h // rows
                right = (c + 1) * w // cols
                bottom = (r + 1) * h // rows
                regions.append((left, top, right, bottom))
        return regions