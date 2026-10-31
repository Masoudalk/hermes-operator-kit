"""
Desktop Bridge Protocol Definitions
TCP localhost IPC protocol for Hermes Desktop Bridge.
"""

from enum import Enum
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any, List
import json
import struct
import uuid


class MessageType(Enum):
    """Message types for bridge communication."""
    # Control messages
    HANDSHAKE = "handshake"
    HANDSHAKE_ACK = "handshake_ack"
    HEALTH = "health"
    HEALTH_RESPONSE = "health_response"
    
    # Capture messages
    CAPTURE_REQUEST = "capture_request"
    CAPTURE_RESPONSE = "capture_response"
    
    # Window management messages
    WINDOW_ENUMERATE = "window_enumerate"
    WINDOW_ENUMERATE_RESPONSE = "window_enumerate_response"
    WINDOW_GET_FOREGROUND = "window_get_foreground"
    WINDOW_GET_FOREGROUND_RESPONSE = "window_get_foreground_response"
    WINDOW_FOCUS = "window_focus"
    WINDOW_FOCUS_RESPONSE = "window_focus_response"
    
    # Error
    ERROR = "error"


class CaptureMode(Enum):
    """Screenshot capture modes."""
    FULL_DESKTOP = "full_desktop"
    WINDOW = "window"
    REGION = "region"


@dataclass
class Message:
    """Base message structure."""
    id: str
    type: MessageType
    payload: dict
    request_id: str = ""
    
    def to_json(self) -> str:
        return json.dumps({
            "id": self.id,
            "type": self.type.value,
            "payload": self.payload,
            "request_id": self.request_id
        }, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> "Message":
        data = json.loads(json_str)
        return cls(
            id=data["id"],
            type=MessageType(data["type"]),
            payload=data.get("payload", {}),
            request_id=data.get("request_id", "")
        )


@dataclass
class HandshakePayload:
    """Handshake payload with authentication token."""
    version: str = "1.0"
    client_name: str = "hermes"
    capabilities: list = None
    auth_token: str = ""  # 32-byte hex token
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = ["capture", "health", "window"]


@dataclass
class HandshakeAckPayload:
    """Handshake acknowledgment payload."""
    version: str = "1.0"
    server_name: str = "desktop-bridge"
    capabilities: list = None
    session_id: str = ""
    auth_required: bool = True
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = ["capture", "health", "window"]


@dataclass
class HealthPayload:
    """Health check payload."""
    auth_token: str = ""


@dataclass
class HealthResponsePayload:
    """Health check response payload."""
    status: str = "healthy"
    uptime_seconds: float = 0.0
    pid: int = 0
    desktop_name: str = ""
    capture_capabilities: list = None
    window_capabilities: list = None
    
    def __post_init__(self):
        if self.capture_capabilities is None:
            self.capture_capabilities = ["full_desktop", "window", "region"]
        if self.window_capabilities is None:
            self.window_capabilities = ["enumerate", "focus", "get_foreground"]


@dataclass
class CaptureRequestPayload:
    """Capture request payload."""
    mode: CaptureMode = CaptureMode.FULL_DESKTOP
    window_title: str = ""
    region: dict = None  # {"left": 0, "top": 0, "right": 1920, "bottom": 1080}
    format: str = "png"  # png, jpeg
    quality: int = 90  # for jpeg
    auth_token: str = ""


@dataclass
class CaptureResponsePayload:
    """Capture response payload - metadata only, image sent separately."""
    success: bool = True
    width: int = 0
    height: int = 0
    format: str = "png"
    size_bytes: int = 0
    mode: CaptureMode = CaptureMode.FULL_DESKTOP
    capture_time_ms: float = 0.0
    error: str = ""


@dataclass
class WindowInfo:
    """Window information structure."""
    hwnd: int
    title: str
    process_name: str
    process_id: int
    visible: bool
    bounds: dict  # {"left": 0, "top": 0, "right": 1920, "bottom": 1080}
    is_foreground: bool = False


@dataclass
class WindowEnumerateResponsePayload:
    """Window enumeration response payload."""
    success: bool = True
    windows: List[dict] = None
    count: int = 0
    error: str = ""
    
    def __post_init__(self):
        if self.windows is None:
            self.windows = []


@dataclass
class WindowGetForegroundResponsePayload:
    """Get foreground window response payload."""
    success: bool = True
    hwnd: int = 0
    title: str = ""
    process_name: str = ""
    process_id: int = 0
    bounds: dict = None
    error: str = ""


@dataclass
class WindowFocusPayload:
    """Window focus request payload."""
    hwnd: int = 0
    auth_token: str = ""


@dataclass
class WindowFocusResponsePayload:
    """Window focus response payload."""
    success: bool = True
    hwnd: int = 0
    title: str = ""
    error: str = ""


class BinaryProtocol:
    """
    Binary protocol for efficient image transport over TCP.
    
    Frame format:
    [4 bytes: magic=0x42524944 ("BRID")]
    [4 bytes: message_type (uint32)]
    [4 bytes: payload_length (uint32)]
    [4 bytes: image_data_length (uint32)]  # 0 if no image
    [payload_length bytes: JSON payload]
    [image_data_length bytes: raw image data]
    """
    
    MAGIC = 0x42524944  # "BRID"
    HEADER_FORMAT = "<IIII"  # magic, msg_type, payload_len, image_len
    HEADER_SIZE = 16
    
    # Message type codes for binary protocol
    MSG_HANDSHAKE = 1
    MSG_HANDSHAKE_ACK = 2
    MSG_HEALTH = 3
    MSG_HEALTH_RESPONSE = 4
    MSG_CAPTURE_REQUEST = 5
    MSG_CAPTURE_RESPONSE = 6
    MSG_WINDOW_ENUMERATE = 7
    MSG_WINDOW_ENUMERATE_RESPONSE = 8
    MSG_WINDOW_GET_FOREGROUND = 9
    MSG_WINDOW_GET_FOREGROUND_RESPONSE = 10
    MSG_WINDOW_FOCUS = 11
    MSG_WINDOW_FOCUS_RESPONSE = 12
    # Mouse/Keyboard (B2)
    MSG_MOUSE_CLICK = 13
    MSG_MOUSE_CLICK_RESPONSE = 14
    MSG_KEYBOARD_TYPE = 15
    MSG_KEYBOARD_TYPE_RESPONSE = 16
    MSG_KEYBOARD_KEY = 17
    MSG_KEYBOARD_KEY_RESPONSE = 18
    # UIA (B2)
    MSG_UIA_FIND_WINDOW = 19
    MSG_UIA_FIND_WINDOW_RESPONSE = 20
    MSG_UIA_FIND_ELEMENT = 21
    MSG_UIA_FIND_ELEMENT_RESPONSE = 22
    MSG_UIA_INVOKE = 23
    MSG_UIA_INVOKE_RESPONSE = 24
    MSG_ERROR = 255
    
    # Protocol limits
    MAX_PAYLOAD_SIZE = 1024 * 1024  # 1 MB
    MAX_IMAGE_SIZE = 50 * 1024 * 1024  # 50 MB
    
    @staticmethod
    def encode_message(msg_type: int, payload: dict, image_data: bytes = b"") -> bytes:
        """Encode a message with optional image data."""
        payload_json = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        payload_len = len(payload_json)
        image_len = len(image_data)
        
        if payload_len > BinaryProtocol.MAX_PAYLOAD_SIZE:
            raise ValueError(f"Payload too large: {payload_len} > {BinaryProtocol.MAX_PAYLOAD_SIZE}")
        if image_len > BinaryProtocol.MAX_IMAGE_SIZE:
            raise ValueError(f"Image too large: {image_len} > {BinaryProtocol.MAX_IMAGE_SIZE}")
        
        header = struct.pack(
            BinaryProtocol.HEADER_FORMAT,
            BinaryProtocol.MAGIC,
            msg_type,
            payload_len,
            image_len
        )
        return header + payload_json + image_data
    
    @staticmethod
    def decode_header(header_bytes: bytes) -> tuple:
        """Decode header, return (msg_type, payload_len, image_len)."""
        if len(header_bytes) != BinaryProtocol.HEADER_SIZE:
            raise ValueError(f"Invalid header size: {len(header_bytes)}")
        
        magic, msg_type, payload_len, image_len = struct.unpack(
            BinaryProtocol.HEADER_FORMAT, header_bytes
        )
        
        if magic != BinaryProtocol.MAGIC:
            raise ValueError(f"Invalid magic: {magic:#x}")
        
        return msg_type, payload_len, image_len
    
    @staticmethod
    def read_frame(sock) -> tuple:
        """
        Read a complete frame from socket.
        Returns (msg_type, payload_dict, image_bytes).
        """
        # Read header
        header_bytes = b""
        while len(header_bytes) < BinaryProtocol.HEADER_SIZE:
            data = sock.recv(BinaryProtocol.HEADER_SIZE - len(header_bytes))
            if not data:
                raise ConnectionError("Socket closed during header read")
            header_bytes += data
        
        msg_type, payload_len, image_len = BinaryProtocol.decode_header(header_bytes)
        
        # Read payload with size limit
        if payload_len > BinaryProtocol.MAX_PAYLOAD_SIZE:
            raise ValueError(f"Payload too large: {payload_len}")
        
        payload_bytes = b""
        while len(payload_bytes) < payload_len:
            data = sock.recv(min(payload_len - len(payload_bytes), 65536))
            if not data:
                raise ConnectionError("Socket closed during payload read")
            payload_bytes += data
        
        payload = json.loads(payload_bytes.decode("utf-8"))
        
        # Read image data with size limit
        if image_len > BinaryProtocol.MAX_IMAGE_SIZE:
            raise ValueError(f"Image too large: {image_len}")
        
        image_data = b""
        while len(image_data) < image_len:
            data = sock.recv(min(image_len - len(image_data), 65536))
            if not data:
                raise ConnectionError("Socket closed during image read")
            image_data += data
        
        return msg_type, payload, image_data
    
    @staticmethod
    def write_frame(sock, msg_type: int, payload: dict, image_data: bytes = b"") -> None:
        """Write a complete frame to socket."""
        frame = BinaryProtocol.encode_message(msg_type, payload, image_data)
        sent = 0
        while sent < len(frame):
            sent_now = sock.send(frame[sent:])
            if sent_now == 0:
                raise ConnectionError("Socket send returned 0")
            sent += sent_now


def create_handshake_request(client_name: str = "hermes", auth_token: str = "") -> Message:
    """Create a handshake request message."""
    return Message(
        id=str(uuid.uuid4()),
        type=MessageType.HANDSHAKE,
        payload=asdict(HandshakePayload(client_name=client_name, auth_token=auth_token)),
        request_id=str(uuid.uuid4())
    )


def create_health_request(auth_token: str = "") -> Message:
    """Create a health check request."""
    return Message(
        id=str(uuid.uuid4()),
        type=MessageType.HEALTH,
        payload=asdict(HealthPayload(auth_token=auth_token)),
        request_id=str(uuid.uuid4())
    )


def create_capture_request(mode: CaptureMode = CaptureMode.FULL_DESKTOP, auth_token: str = "") -> Message:
    """Create a capture request."""
    return Message(
        id=str(uuid.uuid4()),
        type=MessageType.CAPTURE_REQUEST,
        payload=asdict(CaptureRequestPayload(mode=mode, auth_token=auth_token)),
        request_id=str(uuid.uuid4())
    )


def create_window_enumerate_request(auth_token: str = "") -> Message:
    """Create a window enumerate request."""
    return Message(
        id=str(uuid.uuid4()),
        type=MessageType.WINDOW_ENUMERATE,
        payload={"auth_token": auth_token},
        request_id=str(uuid.uuid4())
    )


def create_window_get_foreground_request(auth_token: str = "") -> Message:
    """Create a get foreground window request."""
    return Message(
        id=str(uuid.uuid4()),
        type=MessageType.WINDOW_GET_FOREGROUND,
        payload={"auth_token": auth_token},
        request_id=str(uuid.uuid4())
    )


def create_window_focus_request(hwnd: int, auth_token: str = "") -> Message:
    """Create a window focus request."""
    return Message(
        id=str(uuid.uuid4()),
        type=MessageType.WINDOW_FOCUS,
        payload=asdict(WindowFocusPayload(hwnd=hwnd, auth_token=auth_token)),
        request_id=str(uuid.uuid4())
    )
