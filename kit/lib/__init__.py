"""
Computer Use Universal Library
نظام موحد للتحكم بأي واجهة على Windows
"""

from lib.mouse_controller import MouseController
from lib.vision_layer import VisionLayer
from lib.element_locator import ElementLocator, connect_to_process, start_and_connect
from lib.action_executor import ActionExecutor

__all__ = [
    'MouseController',
    'VisionLayer', 
    'ElementLocator',
    'connect_to_process',
    'start_and_connect',
    'ActionExecutor',
]

__version__ = '1.0.0'