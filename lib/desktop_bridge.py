"""
Desktop Bridge Server - Runs in interactive user session.
Handles screenshot capture, health checks, window management, and IPC via TCP.
"""

import os
import sys
import json
import time
import uuid
import io
import socket
import threading
import logging
import traceback
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
from dataclasses import asdict

# Add lib to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from desktop_bridge_protocol import (
    Message, MessageType, CaptureMode,
    HandshakePayload, HandshakeAckPayload,
    HealthPayload, HealthResponsePayload,
    CaptureRequestPayload, CaptureResponsePayload,
    WindowEnumerateResponsePayload,
    WindowGetForegroundResponsePayload,
    WindowFocusPayload, WindowFocusResponsePayload,
    BinaryProtocol,
    create_handshake_request, create_health_request, create_capture_request,
    create_window_enumerate_request, create_window_get_foreground_request, create_window_focus_request,
)

try:
    import win32pipe
    import win32file
    import win32security
    import win32api
    import win32con
    import win32event
    import pywintypes
    import win32gui
    import win32process
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

try:
    from PIL import ImageGrab, Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import win32gui
    import win32process
    HAS_WIN32GUI = True
except ImportError:
    HAS_WIN32GUI = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("DesktopBridge")


class AuthTokenManager:
    """Manages authentication token storage in user's LocalAppData."""
    
    TOKEN_FILE = "bridge_auth_token"
    TOKEN_DIR = "Hermes"
    
    def __init__(self):
        self.token_path = Path(os.environ.get("LOCALAPPDATA", "")) / self.TOKEN_DIR / self.TOKEN_FILE
    
    def generate_token(self) -> str:
        """Generate a cryptographically random 32-byte token (64 hex chars)."""
        import secrets
        return secrets.token_hex(32)
    
    def save_token(self, token: str) -> bool:
        """Save token to protected LocalAppData directory with owner-only ACL."""
        try:
            self.token_path.parent.mkdir(parents=True, exist_ok=True)
            self.token_path.write_text(token)
            
            # Set owner-only ACL on Windows
            if HAS_WIN32:
                try:
                    import win32security
                    import win32api
                    import win32con
                    
                    # Get current user SID
                    process_token = win32security.OpenProcessToken(
                        win32api.GetCurrentProcess(), 
                        win32con.TOKEN_QUERY
                    )
                    user_sid = win32security.GetTokenInformation(
                        process_token, 
                        win32security.TokenUser
                    )[0]
                    
                    # Create DACL with only owner access
                    dacl = win32security.ACL()
                    dacl.AddAccessAllowedAce(
                        win32security.ACL_REVISION,
                        win32con.GENERIC_READ | win32con.GENERIC_WRITE,
                        user_sid
                    )
                    
                    # Create security descriptor with the DACL
                    sd = win32security.SECURITY_DESCRIPTOR()
                    sd.SetSecurityDescriptorDacl(1, dacl, 0)
                    
                    # Apply to file
                    win32security.SetFileSecurity(
                        str(self.token_path),
                        win32security.DACL_SECURITY_INFORMATION,
                        sd
                    )
                    logger.info(f"Set owner-only ACL on token file")
                except Exception as e:
                    logger.warning(f"Failed to set Windows ACL, falling back to chmod: {e}")
                    try:
                        os.chmod(self.token_path, 0o600)
                    except:
                        pass
            else:
                try:
                    os.chmod(self.token_path, 0o600)
                except:
                    pass
            
            logger.info(f"Auth token saved to {self.token_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save auth token: {e}")
            return False
    
    def load_token(self) -> Optional[str]:
        """Load token from file."""
        try:
            if self.token_path.exists():
                return self.token_path.read_text().strip()
        except Exception as e:
            logger.error(f"Failed to load auth token: {e}")
        return None


class InteractiveDesktop:
    """Manages interactive desktop access for screenshot capture."""
    
    def __init__(self):
        self.desktop_handle = None
        self.original_desktop = None
        self.original_thread_desktop = None
        self._attached = False
    
    def attach(self) -> bool:
        """Attach current thread to interactive desktop (WinSta0\Default)."""
        if not HAS_WIN32:
            logger.error("win32 modules not available")
            return False
        
        try:
            import ctypes
            from ctypes import wintypes
            
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            
            # Setup function signatures
            user32.GetThreadDesktop.argtypes = [wintypes.DWORD]
            user32.GetThreadDesktop.restype = wintypes.HANDLE
            
            user32.OpenInputDesktop.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            user32.OpenInputDesktop.restype = wintypes.HANDLE
            
            user32.SetThreadDesktop.argtypes = [wintypes.HANDLE]
            user32.SetThreadDesktop.restype = wintypes.BOOL
            
            user32.CloseDesktop.argtypes = [wintypes.HANDLE]
            user32.CloseDesktop.restype = wintypes.BOOL
            
            user32.GetUserObjectInformationW.argtypes = [wintypes.HANDLE, wintypes.INT, wintypes.LPVOID, wintypes.DWORD, wintypes.LPDWORD]
            user32.GetUserObjectInformationW.restype = wintypes.BOOL
            
            kernel32.GetCurrentThreadId.argtypes = []
            kernel32.GetCurrentThreadId.restype = wintypes.DWORD
            
            DESKTOP_ALL = 0x01FF
            UOI_NAME = 2
            
            # Save original thread desktop
            thread_id = kernel32.GetCurrentThreadId()
            self.original_thread_desktop = user32.GetThreadDesktop(thread_id)
            
            # Open the interactive desktop - use OpenInputDesktop
            self.desktop_handle = user32.OpenInputDesktop(0, False, DESKTOP_ALL)
            if not self.desktop_handle:
                error = kernel32.GetLastError()
                logger.error(f"Failed to open interactive desktop: {error}")
                return False
            
            # Switch current thread to interactive desktop
            if not user32.SetThreadDesktop(self.desktop_handle):
                error = kernel32.GetLastError()
                logger.error(f"SetThreadDesktop failed: {error}")
                user32.CloseDesktop(self.desktop_handle)
                self.desktop_handle = None
                return False
            
            # Verify we're on the right desktop
            current_desktop = user32.GetThreadDesktop(kernel32.GetCurrentThreadId())
            desktop_name = self._get_desktop_name(current_desktop)
            logger.info(f"Attached to interactive desktop: {desktop_name}")
            
            self._attached = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to attach to interactive desktop: {e}")
            traceback.print_exc()
            return False
    
    def detach(self):
        """Detach from interactive desktop and restore original."""
        if not self._attached:
            return
        
        try:
            import ctypes
            from ctypes import wintypes
            
            user32 = ctypes.windll.user32
            
            user32.SetThreadDesktop.argtypes = [wintypes.HANDLE]
            user32.SetThreadDesktop.restype = wintypes.BOOL
            
            user32.CloseDesktop.argtypes = [wintypes.HANDLE]
            user32.CloseDesktop.restype = wintypes.BOOL
            
            if self.original_thread_desktop:
                user32.SetThreadDesktop(self.original_thread_desktop)
            if self.desktop_handle:
                user32.CloseDesktop(self.desktop_handle)
        except Exception as e:
            logger.warning(f"Error during detach: {e}")
        finally:
            self.desktop_handle = None
            self.original_thread_desktop = None
            self._attached = False
    
    def _get_desktop_name(self, desktop_handle) -> str:
        """Get desktop name from handle."""
        try:
            import ctypes
            from ctypes import wintypes
            
            user32 = ctypes.windll.user32
            user32.GetUserObjectInformationW.argtypes = [wintypes.HANDLE, wintypes.INT, wintypes.LPVOID, wintypes.DWORD, wintypes.LPDWORD]
            user32.GetUserObjectInformationW.restype = wintypes.BOOL
            
            UOI_NAME = 2
            buffer_size = 256
            buffer = ctypes.create_unicode_buffer(buffer_size)
            needed = wintypes.DWORD()
            
            if user32.GetUserObjectInformationW(desktop_handle, UOI_NAME, buffer, buffer_size, ctypes.byref(needed)):
                return buffer.value
            return "Unknown"
        except:
            return "Unknown"
    
    def is_attached(self) -> bool:
        return self._attached
    
    def __enter__(self):
        self.attach()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.detach()


class ScreenshotCapture:
    """Handles screenshot capture using multiple methods."""
    
    def __init__(self, desktop: InteractiveDesktop):
        self.desktop = desktop
    
    def capture_full_desktop(self) -> Tuple[bytes, Dict[str, Any]]:
        """Capture full interactive desktop. Returns (image_bytes, metadata)."""
        if not HAS_PIL:
            raise RuntimeError("PIL/Pillow not available")
        
        if not self.desktop.is_attached():
            raise RuntimeError("Not attached to interactive desktop")
        
        start_time = time.time()
        
        try:
            # Capture full screen
            screenshot = ImageGrab.grab()
            
            # Convert to bytes
            img_bytes = io.BytesIO()
            screenshot.save(img_bytes, format='PNG')
            image_data = img_bytes.getvalue()
            
            capture_time = (time.time() - start_time) * 1000
            
            metadata = {
                "width": screenshot.width,
                "height": screenshot.height,
                "format": "png",
                "size_bytes": len(image_data),
                "mode": "full_desktop",
                "capture_time_ms": capture_time,
            }
            
            logger.info(f"Captured full desktop: {screenshot.width}x{screenshot.height}, "
                       f"{len(image_data)} bytes, {capture_time:.1f}ms")
            
            return image_data, metadata
            
        except Exception as e:
            logger.error(f"Capture failed: {e}")
            raise
    
    def capture_window(self, window_title: str) -> Tuple[bytes, Dict[str, Any]]:
        """Capture specific window by title."""
        if not HAS_PIL or not HAS_WIN32GUI:
            raise RuntimeError("Required modules not available")
        
        if not self.desktop.is_attached():
            raise RuntimeError("Not attached to interactive desktop")
        
        # Find window by title
        hwnd = win32gui.FindWindow(None, window_title)
        if not hwnd:
            raise ValueError(f"Window not found: {window_title}")
        
        # Get window rect
        rect = win32gui.GetWindowRect(hwnd)
        left, top, right, bottom = rect
        width = right - left
        height = bottom - top
        
        start_time = time.time()
        
        try:
            screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
            
            img_bytes = io.BytesIO()
            screenshot.save(img_bytes, format='PNG')
            image_data = img_bytes.getvalue()
            
            capture_time = (time.time() - start_time) * 1000
            
            metadata = {
                "width": width,
                "height": height,
                "format": "png",
                "size_bytes": len(image_data),
                "mode": "window",
                "capture_time_ms": capture_time,
                "window_title": window_title,
            }
            
            return image_data, metadata
            
        except Exception as e:
            logger.error(f"Window capture failed: {e}")
            raise
    
    def validate_image(self, image_data: bytes) -> Dict[str, Any]:
        """Validate captured image has actual content (not all black)."""
        if not HAS_PIL:
            return {"valid": False, "error": "PIL not available"}
        
        try:
            img = Image.open(io.BytesIO(image_data))
            pixels = list(img.getdata())
            
            # Sample pixels
            sample_size = min(10000, len(pixels))
            sample = pixels[:sample_size]
            unique_colors = set(sample)
            
            # Count black/near-black pixels
            black_threshold = 30
            black_pixels = sum(1 for p in sample if all(c < black_threshold for c in p[:3]))
            black_percent = (black_pixels / sample_size) * 100
            
            result = {
                "valid": True,
                "width": img.width,
                "height": img.height,
                "mode": img.mode,
                "unique_colors_sample": len(unique_colors),
                "black_percent": black_percent,
                "has_content": black_percent < 95,  # Less than 95% black = has content
            }
            
            return result
            
        except Exception as e:
            return {"valid": False, "error": str(e)}


class WindowManager:
    """Handles window enumeration, focus, and management."""
    
    def __init__(self, desktop: InteractiveDesktop):
        self.desktop = desktop
    
    def enumerate_windows(self) -> Tuple[List[Dict], int]:
        """Enumerate all visible windows on the interactive desktop.
        Returns (windows_list, count)."""
        if not HAS_WIN32GUI:
            raise RuntimeError("win32gui not available")
        
        if not self.desktop.is_attached():
            raise RuntimeError("Not attached to interactive desktop")
        
        windows = []
        
        def enum_callback(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return True
            
            # Get window title
            title = win32gui.GetWindowText(hwnd)
            if not title:
                return True
            
            # Get window bounds
            try:
                rect = win32gui.GetWindowRect(hwnd)
                left, top, right, bottom = rect
                bounds = {"left": left, "top": top, "right": right, "bottom": bottom}
            except:
                bounds = {"left": 0, "top": 0, "right": 0, "bottom": 0}
            
            # Get process ID and name
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                process_name = ""
                try:
                    import psutil
                    proc = psutil.Process(pid)
                    process_name = proc.name()
                except:
                    try:
                        process_name = win32process.GetModuleFileNameEx(
                            win32api.OpenProcess(0x0400 | 0x0010, False, pid), 0
                        )
                        process_name = os.path.basename(process_name)
                    except:
                        process_name = f"PID:{pid}"
            except:
                pid = 0
                process_name = "Unknown"
            
            # Check if foreground
            is_foreground = (win32gui.GetForegroundWindow() == hwnd)
            
            windows.append({
                "hwnd": hwnd,
                "title": win32gui.GetWindowText(hwnd),
                "process_name": process_name,
                "process_id": pid,
                "visible": True,
                "bounds": bounds,
                "is_foreground": is_foreground
            })
            return True
        
        win32gui.EnumWindows(enum_callback, None)
        
        # Fix bounds for each window
        windows_fixed = []
        for w in windows:
            hwnd = w["hwnd"]
            try:
                rect = win32gui.GetWindowRect(hwnd)
                left, top, right, bottom = rect
                bounds = {"left": left, "top": top, "right": right, "bottom": bottom}
            except:
                bounds = {"left": 0, "top": 0, "right": 0, "bottom": 0}
            
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                process_name = ""
                try:
                    import psutil
                    proc = psutil.Process(pid)
                    process_name = proc.name()
                except:
                    process_name = f"PID:{pid}"
            except:
                pid = 0
                process_name = "Unknown"
            
            is_foreground = (win32gui.GetForegroundWindow() == hwnd)
            
            windows_fixed.append({
                "hwnd": hwnd,
                "title": win32gui.GetWindowText(hwnd),
                "process_name": process_name,
                "process_id": pid,
                "visible": True,
                "bounds": bounds,
                "is_foreground": is_foreground
            })
        
        return windows_fixed, len(windows_fixed)
    
    def get_foreground_window(self) -> Dict:
        """Get the currently active foreground window."""
        if not HAS_WIN32GUI:
            raise RuntimeError("win32gui not available")
        
        if not self.desktop.is_attached():
            raise RuntimeError("Not attached to interactive desktop")
        
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return {"success": False, "error": "No foreground window"}
        
        title = win32gui.GetWindowText(hwnd)
        
        try:
            rect = win32gui.GetWindowRect(hwnd)
            left, top, right, bottom = rect
            bounds = {"left": left, "top": top, "right": right, "bottom": bottom}
        except:
            bounds = {"left": 0, "top": 0, "right": 0, "bottom": 0}
        
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process_name = ""
            try:
                import psutil
                proc = psutil.Process(pid)
                process_name = proc.name()
            except:
                process_name = f"PID:{pid}"
        except:
            pid = 0
            process_name = "Unknown"
        
        return {
            "success": True,
            "hwnd": hwnd,
            "title": title,
            "process_name": process_name,
            "process_id": pid,
            "bounds": bounds
        }
    
    def focus_window(self, hwnd: int) -> Dict:
        """Focus/activate a window by HWND."""
        if not HAS_WIN32GUI:
            raise RuntimeError("win32gui not available")
        
        if not self.desktop.is_attached():
            raise RuntimeError("Not attached to interactive desktop")
        
        if not win32gui.IsWindow(hwnd):
            return {"success": False, "error": f"Invalid HWND: {hwnd}"}
        
        if not win32gui.IsWindowVisible(hwnd):
            return {"success": False, "error": f"Window not visible: {hwnd}"}
        
        try:
            # Get window title before focusing
            title = win32gui.GetWindowText(hwnd)
            
            # Bring window to foreground
            # Use SetForegroundWindow with AttachThreadInput for reliability
            import ctypes
            from ctypes import wintypes
            
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            
            # Get current thread ID
            current_thread = kernel32.GetCurrentThreadId()
            
            # Get foreground window thread
            fg_hwnd = user32.GetForegroundWindow()
            fg_thread = user32.GetWindowThreadProcessId(fg_hwnd, None)
            
            # Attach thread input
            user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
            user32.AttachThreadInput.restype = wintypes.BOOL
            user32.AttachThreadInput(current_thread, fg_thread, True)
            
            # Set foreground
            user32.SetForegroundWindow.argtypes = [wintypes.HWND]
            user32.SetForegroundWindow.restype = wintypes.BOOL
            result = user32.SetForegroundWindow(hwnd)
            
            # Detach thread input
            user32.AttachThreadInput(current_thread, fg_thread, False)
            
            if not result:
                # Try alternative method
                win32gui.SetForegroundWindow(hwnd)
                result = (win32gui.GetForegroundWindow() == hwnd)
            
            if result:
                return {"success": True, "hwnd": hwnd, "title": win32gui.GetWindowText(hwnd)}
            else:
                return {"success": False, "error": "SetForegroundWindow failed"}
                
        except Exception as e:
            logger.error(f"Focus window error: {e}")
            return {"success": False, "error": str(e)}


class AuthTokenManager:
    """Manages authentication token storage in user's LocalAppData."""
    
    TOKEN_FILE = "bridge_auth_token"
    TOKEN_DIR = "Hermes"
    
    def __init__(self):
        self.token_path = Path(os.environ.get("LOCALAPPDATA", "")) / self.TOKEN_DIR / self.TOKEN_FILE
    
    def generate_token(self) -> str:
        """Generate a cryptographically random 32-byte token (64 hex chars)."""
        import secrets
        return secrets.token_hex(32)
    
    def save_token(self, token: str) -> bool:
        """Save token to protected LocalAppData directory with owner-only ACL."""
        try:
            self.token_path.parent.mkdir(parents=True, exist_ok=True)
            self.token_path.write_text(token)
            
            # Set owner-only ACL on Windows
            if HAS_WIN32:
                try:
                    import win32security
                    import win32api
                    import win32con
                    
                    # Get current user SID
                    process_token = win32security.OpenProcessToken(
                        win32api.GetCurrentProcess(), 
                        win32con.TOKEN_QUERY
                    )
                    user_sid = win32security.GetTokenInformation(
                        process_token, 
                        win32security.TokenUser
                    )[0]
                    
                    # Create DACL with only owner access
                    dacl = win32security.ACL()
                    dacl.AddAccessAllowedAce(
                        win32security.ACL_REVISION,
                        win32con.GENERIC_READ | win32con.GENERIC_WRITE,
                        user_sid
                    )
                    
                    # Create security descriptor with the DACL
                    sd = win32security.SECURITY_DESCRIPTOR()
                    sd.SetSecurityDescriptorDacl(1, dacl, 0)
                    
                    # Apply to file
                    win32security.SetFileSecurity(
                        str(self.token_path),
                        win32security.DACL_SECURITY_INFORMATION,
                        sd
                    )
                    logger.info(f"Set owner-only ACL on token file")
                except Exception as e:
                    logger.warning(f"Failed to set Windows ACL, falling back to chmod: {e}")
                    try:
                        os.chmod(self.token_path, 0o600)
                    except:
                        pass
            else:
                try:
                    os.chmod(self.token_path, 0o600)
                except:
                    pass
            
            logger.info(f"Auth token saved to {self.token_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save auth token: {e}")
            return False
    
    def load_token(self) -> Optional[str]:
        """Load token from file."""
        try:
            if self.token_path.exists():
                return self.token_path.read_text().strip()
        except Exception as e:
            logger.error(f"Failed to load auth token: {e}")
        return None


class BridgeServer:
    """TCP server for desktop bridge with authentication."""
    
    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_PORT = 54321
    
    # Connection limits
    MAX_CONNECTIONS = 10
    MAX_CONNECTIONS_PER_IP = 3
    CONNECTION_TIMEOUT = 30
    AUTH_TIMEOUT = 10  # seconds to complete authentication
    
    def __init__(self, desktop: InteractiveDesktop, capture: ScreenshotCapture):
        self.desktop = desktop
        self.capture = capture
        self.window_manager = WindowManager(desktop)
        self.auth_manager = AuthTokenManager()
        self.auth_token = self.auth_manager.load_token() or self.auth_manager.generate_token()
        self.auth_manager.save_token(self.auth_token)
        
        self.server_socket = None
        self.host = self.DEFAULT_HOST
        self.port = self.DEFAULT_PORT
        self.running = False
        self.server_thread = None
        self.client_count = 0
        self.start_time = time.time()
        
        # Connection tracking
        self.active_connections = {}
        self.connection_lock = threading.Lock()
        self._connection_counter = 0
        self._counter_lock = threading.Lock()
        
        logger.info(f"Bridge server initialized with auth token: {self.auth_token[:8]}...")
    
    def _verify_auth(self, payload: dict) -> bool:
        """Verify authentication token from payload."""
        provided_token = payload.get("auth_token", "")
        return provided_token == self.auth_token
    
    def _check_and_register_connection(self, client_ip: str, client_sock) -> int | None:
        """Atomically check connection limits and register connection.
        Returns connection ID if successful, None if rejected.
        """
        with self.connection_lock:
            # Check limits atomically with registration
            if len(self.active_connections) >= self.MAX_CONNECTIONS:
                return None
            
            ip_count = sum(1 for info in self.active_connections.values() if info["ip"] == client_ip)
            if ip_count >= self.MAX_CONNECTIONS_PER_IP:
                return None
            
            # Register connection atomically with unique ID
            with self._counter_lock:
                self._connection_counter += 1
                conn_id = self._connection_counter
            
            self.active_connections[conn_id] = {
                "ip": client_ip,
                "socket": client_sock,
                "connected_at": time.time(),
                "authenticated": False
            }
            return conn_id

    def _check_connection_limits(self, client_ip: str) -> bool:
        """Check if connection limits are exceeded (legacy)."""
        with self.connection_lock:
            if len(self.active_connections) >= self.MAX_CONNECTIONS:
                return False
            
            ip_count = sum(1 for info in self.active_connections.values() if info["ip"] == client_ip)
            if ip_count >= self.MAX_CONNECTIONS_PER_IP:
                return False
            
            return True
    
    def _register_connection(self, client_ip: str, client_sock):
        """Register a new connection (legacy)."""
        with self._counter_lock:
            self._connection_counter += 1
            conn_id = self._connection_counter
        with self.connection_lock:
            self.active_connections[conn_id] = {
                "ip": client_ip,
                "socket": client_sock,
                "connected_at": time.time(),
                "authenticated": False
            }
            return conn_id

    def _unregister_connection(self, conn_id: int):
        """Unregister a connection."""
        with self.connection_lock:
            self.active_connections.pop(conn_id, None)
    
    def _mark_authenticated(self, conn_id: int):
        """Mark connection as authenticated."""
        with self.connection_lock:
            if conn_id in self.active_connections:
                self.active_connections[conn_id]["authenticated"] = True
    
    def start(self, host: str = None, port: int = None) -> bool:
        """Start the TCP server."""
        if host:
            self.host = host
        if port:
            self.port = port
        
        try:
            # Create TCP socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(100)  # Increased backlog for concurrent connections
            
            # Get assigned port if auto-assigned
            if self.port == 0:
                self.port = self.server_socket.getsockname()[1]
            
            logger.info(f"TCP server listening on {self.host}:{self.port}")
            logger.info(f"Auth token (first 8 chars): {self.auth_token[:8]}...")
            
            self.running = True
            self.server_thread = threading.Thread(target=self._server_loop, daemon=True)
            self.server_thread.start()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start TCP server: {e}")
            traceback.print_exc()
            return False
    
    def stop(self):
        """Stop the server."""
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        if self.server_thread:
            self.server_thread.join(timeout=5)
    
    def _server_loop(self):
        """Main server loop - accepts connections and handles requests."""
        logger.info("Server loop started")

        while self.running:
            try:
                # Wait for client connection
                logger.debug("Waiting for client connection...")
                self.server_socket.settimeout(0.1)
                try:
                    client_sock, addr = self.server_socket.accept()
                except socket.timeout:
                    continue
                except OSError:
                    if not self.running:
                        break
                    continue

                client_ip = addr[0]

                # Atomically check connection limits and register connection
                conn_id = self._check_and_register_connection(client_ip, client_sock)
                if conn_id is None:
                    logger.warning(f"Connection rejected: limits exceeded from {client_ip}")
                    try:
                        client_sock.close()
                    except:
                        pass
                    continue

                logger.info(f"Client connected from {addr}")
                self.client_count += 1

                # Handle client in new thread
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_sock, addr, conn_id),
                    daemon=True
                )
                client_thread.start()

            except Exception as e:
                if self.running:
                    logger.error(f"Server loop error: {e}")
                    traceback.print_exc()
                time.sleep(1)  # Brief pause before retry

    def _handle_client(self, client_sock, addr, conn_id):
        """Handle a single client connection."""
        client_ip = addr[0]
        client_id = threading.current_thread().ident
        
        logger.info(f"Handling client {client_id} from {client_ip}")
        
        # Set socket timeout to allow auth deadline checks
        client_sock.settimeout(1.0)
        
        logger.info(f"Client handler started, socket timeout set")
        
        # Attach this thread to interactive desktop for capture operations
        thread_desktop = InteractiveDesktop()
        desktop_attached = thread_desktop.attach()
        if not desktop_attached:
            logger.warning("Failed to attach client handler thread to interactive desktop")
        
        # Track whether connection was successfully registered
        connection_registered = True
        
        try:
            while self.running:
                # Check authentication deadline for unauthenticated connections
                with self.connection_lock:
                    conn_info = self.active_connections.get(conn_id)
                    if conn_info and not conn_info.get("authenticated", False):
                        elapsed = time.time() - conn_info.get("connected_at", time.time())
                        if elapsed >= self.AUTH_TIMEOUT:
                            logger.warning(f"Authentication timeout for client {client_id} from {client_ip} after {elapsed:.1f}s")
                            break
                
                # Read frame with timeout
                try:
                    msg_type, payload, image_data = BinaryProtocol.read_frame(client_sock)
                except ConnectionError:
                    logger.info(f"Client {client_id} disconnected")
                    break
                except socket.timeout:
                    # Socket timeout - continue loop to check auth deadline
                    continue
                except Exception as e:
                    logger.error(f"Read frame error: {e}")
                    break
                
                # Check authentication for non-handshake requests
                if msg_type != BinaryProtocol.MSG_HANDSHAKE:
                    if not self._verify_auth(payload):
                        logger.warning(f"Authentication failed for client {client_id}")
                        error_response = {"error": "Authentication required", "code": "AUTH_REQUIRED"}
                        try:
                            BinaryProtocol.write_frame(client_sock, BinaryProtocol.MSG_ERROR, error_response)
                        except:
                            pass
                        break
                    
                    # Mark as authenticated
                    self._mark_authenticated(conn_id)
                
                # If handshake with valid auth, mark as authenticated
                if msg_type == BinaryProtocol.MSG_HANDSHAKE:
                    provided_token = payload.get("auth_token", "")
                    if provided_token and self._verify_auth({"auth_token": provided_token}):
                        self._mark_authenticated(conn_id)
                
                # Process request (pass thread-local desktop for capture)
                response_type, response_payload, response_image = self._process_request(msg_type, payload, thread_desktop)
                
                # Write response
                try:
                    BinaryProtocol.write_frame(client_sock, response_type, response_payload, response_image)
                except Exception as e:
                    logger.error(f"Write frame error: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Client {client_id} error: {e}")
        finally:
            thread_desktop.detach()
            # Always unregister the connection to prevent leaks
            self._unregister_connection(conn_id)
            try:
                client_sock.close()
            except:
                pass
            logger.info(f"Client {client_id} disconnected")
    
    def _process_request(self, msg_type: int, payload: dict, desktop: InteractiveDesktop = None) -> Tuple[int, dict, bytes]:
        """Process a request and return response."""
        
        if msg_type == BinaryProtocol.MSG_HANDSHAKE:
            return self._handle_handshake(payload)
        elif msg_type == BinaryProtocol.MSG_HEALTH:
            return self._handle_health(payload)
        elif msg_type == BinaryProtocol.MSG_CAPTURE_REQUEST:
            return self._handle_capture(payload, desktop)
        elif msg_type == BinaryProtocol.MSG_WINDOW_ENUMERATE:
            return self._handle_window_enumerate(payload)
        elif msg_type == BinaryProtocol.MSG_WINDOW_GET_FOREGROUND:
            return self._handle_window_get_foreground(payload)
        elif msg_type == BinaryProtocol.MSG_WINDOW_FOCUS:
            return self._handle_window_focus(payload)
        elif msg_type == BinaryProtocol.MSG_MOUSE_CLICK:
            return self._handle_mouse_click(payload)
        elif msg_type == BinaryProtocol.MSG_KEYBOARD_TYPE:
            return self._handle_keyboard_type(payload)
        elif msg_type == BinaryProtocol.MSG_KEYBOARD_KEY:
            return self._handle_keyboard_key(payload)
        elif msg_type == BinaryProtocol.MSG_UIA_FIND_WINDOW:
            return self._handle_uia_find_window(payload)
        elif msg_type == BinaryProtocol.MSG_UIA_FIND_ELEMENT:
            return self._handle_uia_find_element(payload)
        elif msg_type == BinaryProtocol.MSG_UIA_INVOKE:
            return self._handle_uia_invoke(payload)
        else:
            return BinaryProtocol.MSG_ERROR, {"error": f"Unknown message type: {msg_type}"}, b""
    
    def _handle_handshake(self, payload: dict) -> Tuple[int, dict, bytes]:
        """Handle handshake request. Validates auth token if provided.
        Returns auth_valid flag in response. Invalid tokens result in auth_valid=False.
        """
        client_name = payload.get("client_name", "unknown")
        capabilities = payload.get("capabilities", [])
        provided_token = payload.get("auth_token", "")
        
        logger.info(f"Handshake from {client_name}: {capabilities}")
        
        desktop_ok = self.desktop.is_attached()
        
        # Validate auth token if provided
        auth_valid = False
        if provided_token:
            auth_valid = self._verify_auth({"auth_token": provided_token})
            if not auth_valid:
                logger.warning(f"Invalid auth token from {client_name}")
        
        response = {
            "version": "1.0",
            "server_name": "desktop-bridge",
            "capabilities": ["capture", "health", "window"],
            "session_id": str(uuid.uuid4()),
            "desktop_attached": desktop_ok,
            "server_pid": os.getpid(),
            "auth_required": True,
            "authenticated": auth_valid
        }
        
        return BinaryProtocol.MSG_HANDSHAKE_ACK, response, b""
    
    def _handle_health(self, payload: dict) -> Tuple[int, dict, bytes]:
        """Handle health check."""
        uptime = time.time() - self.start_time
        
        desktop_name = ""
        if self.desktop.desktop_handle:
            desktop_name = self.capture.desktop._get_desktop_name(self.desktop.desktop_handle)
        
        response = {
            "status": "healthy",
            "uptime_seconds": uptime,
            "pid": os.getpid(),
            "desktop_name": desktop_name,
            "capture_capabilities": ["full_desktop", "window"],
            "window_capabilities": ["enumerate", "focus", "get_foreground"]
        }
        
        return BinaryProtocol.MSG_HEALTH_RESPONSE, response, b""
    
    def _handle_capture(self, payload: dict, desktop: InteractiveDesktop = None) -> Tuple[int, dict, bytes]:
        """Handle capture request."""
        mode = CaptureMode(payload.get("mode", "full_desktop"))
        window_title = payload.get("window_title", "")
        
        start_time = time.time()
        image_data = b""
        metadata = {}
        error = ""
        
        try:
            capture_desktop = desktop if desktop else self.desktop
            capture = ScreenshotCapture(capture_desktop)
            
            if mode == CaptureMode.FULL_DESKTOP:
                image_data, metadata = capture.capture_full_desktop()
            elif mode == CaptureMode.WINDOW and window_title:
                image_data, metadata = capture.capture_window(window_title)
            else:
                error = f"Unsupported capture mode: {mode}"
                
        except Exception as e:
            error = str(e)
            logger.error(f"Capture error: {e}")
            traceback.print_exc()
        
        capture_time_ms = (time.time() - start_time) * 1000
        
        if image_data:
            validation = ScreenshotCapture(capture_desktop).validate_image(image_data)
            metadata["validation"] = validation
            
            response = {
                "success": True,
                "width": metadata.get("width", 0),
                "height": metadata.get("height", 0),
                "format": metadata.get("format", "png"),
                "size_bytes": len(image_data),
                "mode": metadata.get("mode", "full_desktop"),
                "capture_time_ms": capture_time_ms,
            }
        else:
            response = {
                "success": False,
                "error": error or "Capture failed",
                "capture_time_ms": capture_time_ms,
            }
        
        return BinaryProtocol.MSG_CAPTURE_RESPONSE, response, image_data
    
    def _handle_window_enumerate(self, payload: dict) -> Tuple[int, dict, bytes]:
        """Handle window enumeration request."""
        try:
            windows, count = self.window_manager.enumerate_windows()
            
            response = {
                "success": True,
                "windows": windows,
                "count": count
            }
            
        except Exception as e:
            logger.error(f"Window enumerate error: {e}")
            traceback.print_exc()
            response = {
                "success": False,
                "error": str(e)
            }
        
        return BinaryProtocol.MSG_WINDOW_ENUMERATE_RESPONSE, response, b""
    
    def _handle_window_get_foreground(self, payload: dict) -> Tuple[int, dict, bytes]:
        """Handle get foreground window request."""
        try:
            result = self.window_manager.get_foreground_window()
            
            response = {
                "success": result.get("success", False),
                "hwnd": result.get("hwnd", 0),
                "title": result.get("title", ""),
                "process_name": result.get("process_name", ""),
                "process_id": result.get("process_id", 0),
                "bounds": result.get("bounds"),
                "error": result.get("error", "")
            }
            
        except Exception as e:
            logger.error(f"Get foreground window error: {e}")
            traceback.print_exc()
            response = {
                "success": False,
                "error": str(e)
            }
        
        return BinaryProtocol.MSG_WINDOW_GET_FOREGROUND_RESPONSE, response, b""
    
    def _handle_window_focus(self, payload: dict) -> Tuple[int, dict, bytes]:
        """Handle window focus request."""
        hwnd = payload.get("hwnd", 0)
        
        try:
            result = self.window_manager.focus_window(hwnd)
            
            response = {
                "success": result.get("success", False),
                "hwnd": result.get("hwnd", 0),
                "title": result.get("title", ""),
                "error": result.get("error", "")
            }
            
        except Exception as e:
            logger.error(f"Focus window error: {e}")
            traceback.print_exc()
            response = {
                "success": False,
                "error": str(e)
            }
        
        return BinaryProtocol.MSG_WINDOW_FOCUS_RESPONSE, response, b""


def create_bridge_server(desktop: InteractiveDesktop = None) -> BridgeServer:
    """Factory function to create configured bridge server."""
    if desktop is None:
        desktop = InteractiveDesktop()
    capture = ScreenshotCapture(desktop)
    return BridgeServer(desktop, capture)


def main():
    """Main entry point for desktop bridge."""
    import signal
    import threading
    
    shutdown_event = threading.Event()
    

    def _handle_mouse_click(self, payload: dict) -> Tuple[int, dict, bytes]:
        """Handle mouse click request."""
        import ctypes
        x = payload.get("x", 0)
        y = payload.get("y", 0)
        button = payload.get("button", "left")
        
        try:
            user32 = ctypes.windll.user32
            # Move cursor
            user32.SetCursorPos(x, y)
            time.sleep(0.05)
            
            # Click
            if button == "left":
                user32.mouse_event(0x0002, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTDOWN
                time.sleep(0.05)
                user32.mouse_event(0x0004, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTUP
            elif button == "right":
                user32.mouse_event(0x0008, 0, 0, 0, 0)  # MOUSEEVENTF_RIGHTDOWN
                time.sleep(0.05)
                user32.mouse_event(0x0010, 0, 0, 0, 0)  # MOUSEEVENTF_RIGHTUP
            
            return BinaryProtocol.MSG_MOUSE_CLICK_RESPONSE, {"success": True, "x": x, "y": y}, b""
        except Exception as e:
            return BinaryProtocol.MSG_MOUSE_CLICK_RESPONSE, {"success": False, "error": str(e)}, b""
    
    def _handle_keyboard_type(self, payload: dict) -> Tuple[int, dict, bytes]:
        """Handle keyboard type request using clipboard."""
        text = payload.get("text", "")
        try:
            import ctypes
            # Set clipboard
            # Use win32clipboard if available, else ctypes
            try:
                import win32clipboard
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
                win32clipboard.CloseClipboard()
            except ImportError:
                # Fallback: use PowerShell
                import subprocess
                subprocess.run(["powershell", "-command", f"Set-Clipboard -Value '{text}'"], capture_output=True, timeout=5)
            
            # Send Ctrl+V
            user32 = ctypes.windll.user32
            VK_CONTROL = 0x11
            VK_V = 0x56
            user32.keybd_event(VK_CONTROL, 0, 0, 0)
            user32.keybd_event(VK_V, 0, 0, 0)
            time.sleep(0.05)
            user32.keybd_event(VK_V, 0, 2, 0)
            user32.keybd_event(VK_CONTROL, 0, 2, 0)
            
            return BinaryProtocol.MSG_KEYBOARD_TYPE_RESPONSE, {"success": True, "length": len(text)}, b""
        except Exception as e:
            return BinaryProtocol.MSG_KEYBOARD_TYPE_RESPONSE, {"success": False, "error": str(e)}, b""
    
    def _handle_keyboard_key(self, payload: dict) -> Tuple[int, dict, bytes]:
        """Handle keyboard key press request."""
        keys = payload.get("keys", "")
        try:
            import ctypes
            user32 = ctypes.windll.user32
            
            # Parse key combo (e.g., "ctrl+s", "enter", "tab")
            key_map = {
                "enter": 0x0D, "tab": 0x09, "escape": 0x1B, "backspace": 0x08,
                "delete": 0x2E, "space": 0x20, "up": 0x26, "down": 0x28,
                "left": 0x25, "right": 0x27, "home": 0x24, "end": 0x23,
                "pageup": 0x21, "pagedown": 0x22, "f1": 0x70, "f2": 0x71,
                "f3": 0x72, "f4": 0x73, "f5": 0x74, "f6": 0x75,
            }
            
            parts = keys.lower().split("+")
            modifiers = []
            main_key = None
            
            for part in parts:
                part = part.strip()
                if part in ("ctrl", "control"):
                    modifiers.append(0x11)  # VK_CONTROL
                elif part in ("alt",):
                    modifiers.append(0x12)  # VK_MENU
                elif part in ("shift",):
                    modifiers.append(0x10)  # VK_SHIFT
                elif part in ("win", "windows", "super"):
                    modifiers.append(0x5B)  # VK_LWIN
                else:
                    main_key = key_map.get(part, None)
                    if main_key is None:
                        # Try as single char
                        if len(part) == 1:
                            main_key = ord(part.upper())
            
            # Press modifiers
            for mod in modifiers:
                user32.keybd_event(mod, 0, 0, 0)
            
            # Press main key
            if main_key:
                user32.keybd_event(main_key, 0, 0, 0)
                time.sleep(0.05)
                user32.keybd_event(main_key, 0, 2, 0)
            
            # Release modifiers
            for mod in reversed(modifiers):
                user32.keybd_event(mod, 0, 2, 0)
            
            return BinaryProtocol.MSG_KEYBOARD_KEY_RESPONSE, {"success": True, "keys": keys}, b""
        except Exception as e:
            return BinaryProtocol.MSG_KEYBOARD_KEY_RESPONSE, {"success": False, "error": str(e)}, b""
    
    def _handle_uia_find_window(self, payload: dict) -> Tuple[int, dict, bytes]:
        """Handle UIA find window request."""
        title = payload.get("title", "")
        process_name = payload.get("process_name", "")
        
        try:
            import ctypes
            from ctypes import wintypes
            
            # Enumerate windows
            windows = []
            def enum_callback(hwnd, _):
                if ctypes.windll.user32.IsWindowVisible(hwnd):
                    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buf = ctypes.create_unicode_buffer(length + 1)
                        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                        window_title = buf.value
                        pid = wintypes.DWORD()
                        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                        
                        match = True
                        if title and title not in window_title:
                            match = False
                        if process_name:
                            # Get process name from PID
                            try:
                                import psutil
                                proc = psutil.Process(pid.value)
                                if process_name.lower() not in proc.name().lower():
                                    match = False
                            except:
                                pass
                        
                        if match:
                            windows.append({"hwnd": hwnd, "title": window_title, "pid": pid.value})
                return True
            
            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
            ctypes.windll.user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
            
            return BinaryProtocol.MSG_UIA_FIND_WINDOW_RESPONSE, {"success": True, "windows": windows, "count": len(windows)}, b""
        except Exception as e:
            return BinaryProtocol.MSG_UIA_FIND_WINDOW_RESPONSE, {"success": False, "error": str(e)}, b""
    
    def _handle_uia_find_element(self, payload: dict) -> Tuple[int, dict, bytes]:
        """Handle UIA find element request (basic - returns window info)."""
        hwnd = payload.get("hwnd")
        auto_id = payload.get("auto_id")
        control_type = payload.get("control_type")
        
        if not hwnd:
            return BinaryProtocol.MSG_UIA_FIND_ELEMENT_RESPONSE, {"success": False, "error": "hwnd required"}, b""
        
        # Basic implementation - just verify window exists
        try:
            import ctypes
            if ctypes.windll.user32.IsWindow(hwnd):
                return BinaryProtocol.MSG_UIA_FIND_ELEMENT_RESPONSE, {
                    "success": True, "found": True, "hwnd": hwnd,
                    "auto_id": auto_id, "control_type": control_type
                }, b""
            else:
                return BinaryProtocol.MSG_UIA_FIND_ELEMENT_RESPONSE, {"success": False, "error": "Window not found"}, b""
        except Exception as e:
            return BinaryProtocol.MSG_UIA_FIND_ELEMENT_RESPONSE, {"success": False, "error": str(e)}, b""
    
    def _handle_uia_invoke(self, payload: dict) -> Tuple[int, dict, bytes]:
        """Handle UIA invoke request (basic - sends WM_COMMAND)."""
        hwnd = payload.get("hwnd")
        if not hwnd:
            return BinaryProtocol.MSG_UIA_INVOKE_RESPONSE, {"success": False, "error": "hwnd required"}, b""
        
        try:
            import ctypes
            # Send WM_COMMAND (0x0111) with ID 0 (default action)
            ctypes.windll.user32.SendMessageW(hwnd, 0x0111, 0, 0)
            return BinaryProtocol.MSG_UIA_INVOKE_RESPONSE, {"success": True}, b""
        except Exception as e:
            return BinaryProtocol.MSG_UIA_INVOKE_RESPONSE, {"success": False, "error": str(e)}, b""


    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        shutdown_event.set()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("=" * 60)
    logger.info("Hermes Desktop Bridge - Phase 1C-B1")
    logger.info("Starting in interactive user session")
    logger.info("=" * 60)
    
    # Step 1: Attach to interactive desktop
    logger.info("Attaching to interactive desktop (WinSta0\Default)...")
    desktop = InteractiveDesktop()
    if not desktop.attach():
        logger.error("Failed to attach to interactive desktop. Exiting.")
        return 1
    
    logger.info("Successfully attached to interactive desktop")
    
    # Step 2: Create and start bridge server
    logger.info("Creating bridge server...")
    server = create_bridge_server()
    
    logger.info("Starting TCP server...")
    if not server.start():
        logger.error("Failed to start TCP server. Exiting.")
        desktop.detach()
        return 1
    
    logger.info("Bridge server started successfully")
    logger.info(f"TCP: {server.host}:{server.port}")
    logger.info(f"Server PID: {os.getpid()}")
    logger.info("Waiting for client connections...")
    
    # Wait for shutdown
    try:
        shutdown_event.wait()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    
    # Cleanup
    logger.info("Shutting down...")
    server.stop()
    desktop.detach()
    logger.info("Desktop bridge stopped")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
