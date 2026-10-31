"""
Capability Registry - Central registry for all execution capabilities.
Each tool declares its capabilities, contracts, and metadata.
"""
from __future__ import annotations
import json
import uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from enum import Enum
from pathlib import Path


class BackendType(Enum):
    """Execution backend types."""
    NATIVE_CLI = "native_cli"
    CLI_ANYTHING = "cli_anything"
    WINDOWS_UIA = "windows_uia"
    DESKTOP_BRIDGE = "desktop_bridge"
    MOUSE_KEYBOARD = "mouse_keyboard"
    BROWSER_DOM = "browser_dom"
    BROWSER_CDP = "browser_cdp"
    MCP = "mcp"
    API = "api"
    SCREENSHOT_VISION = "screenshot_vision"
    OCR = "ocr"
    FILESYSTEM = "filesystem"


class CapabilityCategory(Enum):
    """High-level capability categories."""
    LAUNCH = "launch"
    INSPECT = "inspect"
    INTERACT = "interact"
    CAPTURE = "capture"
    VERIFY = "verify"
    FILE_OPS = "file_ops"
    RESEARCH = "research"
    CODE = "code"


@dataclass
class ToolContract:
    """Contract for a single tool/capability."""
    tool_id: str
    name: str
    description: str
    version: str = "1.0.0"
    
    # I/O schemas
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    
    # Capabilities
    capabilities: List[CapabilityCategory] = field(default_factory=list)
    supported_applications: List[str] = field(default_factory=list)  # Empty = universal
    
    # Backend
    backend: BackendType = BackendType.NATIVE_CLI
    platform: List[str] = field(default_factory=lambda: ["windows"])
    
    # Requirements
    permissions: List[str] = field(default_factory=list)  # e.g., ["admin", "ui_access"]
    dependencies: List[str] = field(default_factory=list)  # e.g., ["pywinauto", "pillow"]
    
    # Risk and limits
    risk_level: str = "low"  # low, medium, high, critical
    timeout_seconds: int = 30
    max_retries: int = 3
    idempotent: bool = False
    
    # Verification
    verification_methods: List[str] = field(default_factory=list)  # e.g., ["clipboard_sentinel", "uia_state", "vision"]
    rollback_capable: bool = False
    
    # Status
    test_status: str = "untested"  # untested, partial, verified
    reliability_score: float = 0.0  # 0.0-1.0
    
    # Metadata
    source_file: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["capabilities"] = [c.value for c in self.capabilities]
        d["backend"] = self.backend.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolContract":
        data = data.copy()
        data["capabilities"] = [CapabilityCategory(c) for c in data.get("capabilities", [])]
        data["backend"] = BackendType(data.get("backend", "native_cli"))
        return cls(**data)


class CapabilityRegistry:
    """Central registry for all available tools and their capabilities."""
    
    def __init__(self, registry_path: Optional[str] = None):
        self.tools: Dict[str, ToolContract] = {}
        self.registry_path = registry_path or "C:/agent-work/agent_core/capability_registry/registry.json"
        self._load()
    
    def _load(self):
        """Load registry from disk."""
        path = Path(self.registry_path)
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for tool_data in data.get("tools", []):
                    tool = ToolContract.from_dict(tool_data)
                    self.tools[tool.tool_id] = tool
                print(f"Loaded {len(self.tools)} tools from registry")
            except Exception as e:
                print(f"Failed to load registry: {e}")
        else:
            print("No existing registry found, starting fresh")
    
    def save(self):
        """Save registry to disk."""
        path = Path(self.registry_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": "1.0",
            "tools": [tool.to_dict() for tool in self.tools.values()]
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(self.tools)} tools to registry")
    
    def register(self, tool: ToolContract) -> bool:
        """Register a new tool or update existing."""
        if tool.tool_id in self.tools:
            print(f"Updating existing tool: {tool.tool_id}")
        else:
            print(f"Registering new tool: {tool.tool_id}")
        self.tools[tool.tool_id] = tool
        self.save()
        return True
    
    def unregister(self, tool_id: str) -> bool:
        """Unregister a tool."""
        if tool_id in self.tools:
            del self.tools[tool_id]
            self.save()
            print(f"Unregistered tool: {tool_id}")
            return True
        return False
    
    def get(self, tool_id: str) -> Optional[ToolContract]:
        """Get a tool by ID."""
        return self.tools.get(tool_id)
    
    def list_all(self) -> List[ToolContract]:
        """List all registered tools."""
        return list(self.tools.values())
    
    def list_by_capability(self, capability: CapabilityCategory) -> List[ToolContract]:
        """List tools that have a specific capability."""
        return [t for t in self.tools.values() if capability in t.capabilities]
    
    def list_by_backend(self, backend: BackendType) -> List[ToolContract]:
        """List tools that use a specific backend."""
        return [t for t in self.tools.values() if t.backend == backend]
    
    def list_by_application(self, app_name: str) -> List[ToolContract]:
        """List tools that support a specific application."""
        return [t for t in self.tools.values() 
                if not t.supported_applications or app_name.lower() in [a.lower() for a in t.supported_applications]]


# Default tool contracts for existing Operator Kit and Bridge capabilities
def create_default_contracts() -> List[ToolContract]:
    """Create default tool contracts for existing capabilities."""
    from datetime import datetime
    now = datetime.now().isoformat()
    
    contracts = [
        # ===== NATIVE CLI TOOLS =====
        ToolContract(
            tool_id="cli.winver",
            name="Windows Version",
            description="Display Windows version information",
            capabilities=[CapabilityCategory.INSPECT],
            backend=BackendType.NATIVE_CLI,
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {"version": {"type": "string"}}},
            supported_applications=["winver.exe"],
            risk_level="low",
            timeout_seconds=5,
            verification_methods=["exit_code", "output_parsing"],
            test_status="verified",
            reliability_score=0.99,
            source_file="lib/safe_gui_ctl.py",
            created_at=now,
            updated_at=now,
        ),
        
        ToolContract(
            tool_id="cli.charmap",
            name="Character Map",
            description="Open Windows Character Map utility",
            capabilities=[CapabilityCategory.LAUNCH, CapabilityCategory.INSPECT],
            backend=BackendType.NATIVE_CLI,
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {"pid": {"type": "integer"}}},
            supported_applications=["charmap.exe"],
            risk_level="low",
            timeout_seconds=10,
            verification_methods=["pid_tracking", "window_verify"],
            test_status="verified",
            reliability_score=0.98,
            source_file="lib/safe_gui_ctl.py",
            created_at=now,
            updated_at=now,
        ),
        
        ToolContract(
            tool_id="cli.notepad",
            name="Notepad",
            description="Open Windows Notepad",
            capabilities=[CapabilityCategory.LAUNCH, CapabilityCategory.INTERACT, CapabilityCategory.VERIFY],
            backend=BackendType.NATIVE_CLI,
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {"pid": {"type": "integer"}}},
            supported_applications=["notepad.exe"],
            risk_level="low",
            timeout_seconds=10,
            verification_methods=["pid_tracking", "window_verify", "clipboard_sentinel"],
            test_status="verified",
            reliability_score=0.95,
            source_file="lib/safe_gui_ctl.py",
            created_at=now,
            updated_at=now,
        ),
        
        # ===== WINDOWS UIA TOOLS =====
        ToolContract(
            tool_id="uia.enumerate_windows",
            name="Enumerate Windows",
            description="Enumerate all visible windows with metadata",
            capabilities=[CapabilityCategory.INSPECT],
            backend=BackendType.WINDOWS_UIA,
            input_schema={"type": "object", "properties": {}},
            output_schema={
                "type": "object",
                "properties": {
                    "windows": {"type": "array", "items": {"type": "object"}},
                    "count": {"type": "integer"}
                }
            },
            risk_level="low",
            timeout_seconds=10,
            verification_methods=["cross_reference_pid", "foreground_check"],
            test_status="verified",
            reliability_score=0.92,
            source_file="lib/win_app_ops.py",
            created_at=now,
            updated_at=now,
        ),
        
        ToolContract(
            tool_id="uia.focus_window",
            name="Focus Window",
            description="Focus/activate a window by HWND",
            capabilities=[CapabilityCategory.INTERACT],
            backend=BackendType.WINDOWS_UIA,
            input_schema={
                "type": "object",
                "properties": {"hwnd": {"type": "integer"}},
                "required": ["hwnd"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "hwnd": {"type": "integer"},
                    "title": {"type": "string"}
                }
            },
            risk_level="medium",
            timeout_seconds=5,
            verification_methods=["foreground_check", "screenshot_verify"],
            test_status="verified",
            reliability_score=0.88,
            source_file="lib/win_app_ops.py",
            created_at=now,
            updated_at=now,
        ),
        
        ToolContract(
            tool_id="uia.get_foreground",
            name="Get Foreground Window",
            description="Get the currently active foreground window",
            capabilities=[CapabilityCategory.INSPECT],
            backend=BackendType.WINDOWS_UIA,
            input_schema={"type": "object", "properties": {}},
            output_schema={
                "type": "object",
                "properties": {
                    "hwnd": {"type": "integer"},
                    "title": {"type": "string"},
                    "process_name": {"type": "string"},
                    "process_id": {"type": "integer"},
                    "bounds": {"type": "object"}
                }
            },
            risk_level="low",
            timeout_seconds=5,
            verification_methods=["cross_reference_pid"],
            test_status="verified",
            reliability_score=0.95,
            source_file="lib/win_app_ops.py",
            created_at=now,
            updated_at=now,
        ),
        
        # ===== DESKTOP BRIDGE TOOLS =====
        ToolContract(
            tool_id="bridge.capture_desktop",
            name="Capture Full Desktop",
            description="Capture full desktop screenshot via Desktop Bridge",
            capabilities=[CapabilityCategory.CAPTURE, CapabilityCategory.VERIFY],
            backend=BackendType.DESKTOP_BRIDGE,
            input_schema={
                "type": "object",
                "properties": {
                    "mode": {"type": "string", "enum": ["full_desktop", "window", "region"]},
                    "window_title": {"type": "string"},
                    "region": {"type": "object"}
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "image_data": {"type": "string", "format": "binary"},
                    "width": {"type": "integer"},
                    "height": {"type": "integer"},
                    "format": {"type": "string"},
                    "size_bytes": {"type": "integer"},
                    "capture_time_ms": {"type": "number"},
                    "validation": {"type": "object"}
                }
            },
            risk_level="low",
            timeout_seconds=30,
            verification_methods=["image_validation", "black_pixel_check", "color_count"],
            test_status="verified",
            reliability_score=0.90,
            source_file="lib/desktop_bridge.py",
            created_at=now,
            updated_at=now,
        ),
        
        ToolContract(
            tool_id="bridge.window_enumerate",
            name="Bridge Window Enumerate",
            description="Enumerate windows via Desktop Bridge",
            capabilities=[CapabilityCategory.INSPECT],
            backend=BackendType.DESKTOP_BRIDGE,
            input_schema={"type": "object", "properties": {}},
            output_schema={
                "type": "object",
                "properties": {
                    "windows": {"type": "array"},
                    "count": {"type": "integer"}
                }
            },
            risk_level="low",
            timeout_seconds=10,
            verification_methods=["cross_reference_uia"],
            test_status="verified",
            reliability_score=0.90,
            source_file="lib/desktop_bridge.py",
            created_at=now,
            updated_at=now,
        ),
        
        ToolContract(
            tool_id="bridge.window_focus",
            name="Bridge Window Focus",
            description="Focus window via Desktop Bridge",
            capabilities=[CapabilityCategory.INTERACT],
            backend=BackendType.DESKTOP_BRIDGE,
            input_schema={
                "type": "object",
                "properties": {"hwnd": {"type": "integer"}},
                "required": ["hwnd"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "hwnd": {"type": "integer"},
                    "title": {"type": "string"}
                }
            },
            risk_level="medium",
            timeout_seconds=10,
            verification_methods=["screenshot_verify", "foreground_check"],
            test_status="verified",
            reliability_score=0.88,
            source_file="lib/desktop_bridge.py",
            created_at=now,
            updated_at=now,
        ),
        
        ToolContract(
            tool_id="bridge.capture_window",
            name="Bridge Capture Window",
            description="Capture specific window via Desktop Bridge",
            capabilities=[CapabilityCategory.CAPTURE, CapabilityCategory.VERIFY],
            backend=BackendType.DESKTOP_BRIDGE,
            input_schema={
                "type": "object",
                "properties": {
                    "window_title": {"type": "string"}
                },
                "required": ["window_title"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "image_data": {"type": "string", "format": "binary"},
                    "width": {"type": "integer"},
                    "height": {"type": "integer"},
                    "format": {"type": "string"},
                    "size_bytes": {"type": "integer"},
                    "capture_time_ms": {"type": "number"},
                    "validation": {"type": "object"}
                }
            },
            risk_level="low",
            timeout_seconds=30,
            verification_methods=["image_validation", "black_pixel_check"],
            test_status="verified",
            reliability_score=0.88,
            source_file="lib/desktop_bridge.py",
            created_at=now,
            updated_at=now,
        ),
        
        # ===== MOUSE/KEYBOARD TOOLS =====
        ToolContract(
            tool_id="input.click",
            name="Mouse Click",
            description="Real mouse click at coordinates",
            capabilities=[CapabilityCategory.INTERACT],
            backend=BackendType.MOUSE_KEYBOARD,
            input_schema={
                "type": "object",
                "properties": {
                    "x": {"type": "integer"},
                    "y": {"type": "integer"},
                    "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"}
                },
                "required": ["x", "y"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "position": {"type": "object"}
                }
            },
            risk_level="medium",
            timeout_seconds=5,
            verification_methods=["screenshot_verify", "cursor_position_check"],
            test_status="verified",
            reliability_score=0.85,
            source_file="lib/win_app_ops.py",
            created_at=now,
            updated_at=now,
        ),
        
        ToolContract(
            tool_id="input.type_text",
            name="Type Text via Clipboard",
            description="Type text using clipboard paste (clipboard sentinel verification)",
            capabilities=[CapabilityCategory.INTERACT, CapabilityCategory.VERIFY],
            backend=BackendType.MOUSE_KEYBOARD,
            input_schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "maxLength": 10000},
                    "app_key": {"type": "string"}
                },
                "required": ["text", "app_key"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "verified": {"type": "boolean"},
                    "match": {"type": "boolean"}
                }
            },
            risk_level="low",
            timeout_seconds=10,
            verification_methods=["clipboard_sentinel", "clipboard_verify"],
            test_status="verified",
            reliability_score=0.98,
            source_file="lib/win_app_ops.py",
            created_at=now,
            updated_at=now,
        ),
        
        ToolContract(
            tool_id="input.verify_text",
            name="Verify Text via Clipboard",
            description="Verify text in editor via clipboard sentinel pattern",
            capabilities=[CapabilityCategory.VERIFY],
            backend=BackendType.MOUSE_KEYBOARD,
            input_schema={
                "type": "object",
                "properties": {
                    "expected": {"type": "string", "maxLength": 10000},
                    "app_key": {"type": "string"}
                },
                "required": ["expected", "app_key"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "match": {"type": "boolean"},
                    "read": {"type": "string"},
                    "verified": {"type": "boolean"}
                }
            },
            risk_level="low",
            timeout_seconds=5,
            verification_methods=["clipboard_sentinel"],
            test_status="verified",
            reliability_score=0.99,
            source_file="lib/win_app_ops.py",
            created_at=now,
            updated_at=now,
        ),
        
        ToolContract(
            tool_id="input.clear_editor",
            name="Clear Editor",
            description="Clear editor content (Ctrl+A, Delete)",
            capabilities=[CapabilityCategory.INTERACT],
            backend=BackendType.MOUSE_KEYBOARD,
            input_schema={
                "type": "object",
                "properties": {
                    "app_key": {"type": "string"}
                },
                "required": ["app_key"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"}
                }
            },
            risk_level="low",
            timeout_seconds=5,
            verification_methods=["clipboard_sentinel"],
            test_status="verified",
            reliability_score=0.95,
            source_file="lib/win_app_ops.py",
            created_at=now,
            updated_at=now,
        ),
        
        # ===== VISION/OCR TOOLS =====
        ToolContract(
            tool_id="vision.analyze_screenshot",
            name="Analyze Screenshot with Vision Model",
            description="Analyze screenshot using NVIDIA vision model",
            capabilities=[CapabilityCategory.CAPTURE, CapabilityCategory.VERIFY, CapabilityCategory.RESEARCH],
            backend=BackendType.SCREENSHOT_VISION,
            input_schema={
                "type": "object",
                "properties": {
                    "image_path": {"type": "string"},
                    "question": {"type": "string"}
                },
                "required": ["image_path", "question"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "answer": {"type": "string"},
                    "confidence": {"type": "number"}
                }
            },
            risk_level="low",
            timeout_seconds=60,
            verification_methods=["cross_reference_ocr", "human_review"],
            test_status="partial",  # Vision works but Arabic OCR fails at low res
            reliability_score=0.60,
            source_file="lib/vision_layer.py",
            created_at=now,
            updated_at=now,
        ),
        
        ToolContract(
            tool_id="ocr.tesseract",
            name="Tesseract OCR",
            description="Local OCR via Tesseract",
            capabilities=[CapabilityCategory.CAPTURE, CapabilityCategory.VERIFY],
            backend=BackendType.OCR,
            input_schema={
                "type": "object",
                "properties": {
                    "image_path": {"type": "string"},
                    "lang": {"type": "string", "default": "eng+ara"}
                },
                "required": ["image_path"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "confidence": {"type": "number"}
                }
            },
            dependencies=["tesseract", "pytesseract"],
            risk_level="low",
            timeout_seconds=30,
            verification_methods=["cross_reference_vision"],
            test_status="untested",
            reliability_score=0.50,
            source_file="lib/vision_layer.py",
            created_at=now,
            updated_at=now,
        ),
        
        # ===== FILESYSTEM TOOLS =====
        ToolContract(
            tool_id="fs.read_file",
            name="Read File",
            description="Read file contents",
            capabilities=[CapabilityCategory.FILE_OPS],
            backend=BackendType.FILESYSTEM,
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "offset": {"type": "integer", "default": 1},
                    "limit": {"type": "integer", "default": 2000}
                },
                "required": ["path"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "total_lines": {"type": "integer"}
                }
            },
            risk_level="low",
            timeout_seconds=10,
            verification_methods=["content_hash", "line_count"],
            test_status="verified",
            reliability_score=1.0,
            source_file="lib/safe_gui_ctl.py",
            created_at=now,
            updated_at=now,
        ),
        
        ToolContract(
            tool_id="fs.write_file",
            name="Write File",
            description="Write file contents",
            capabilities=[CapabilityCategory.FILE_OPS],
            backend=BackendType.FILESYSTEM,
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["path", "content"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "path": {"type": "string"}
                }
            },
            risk_level="medium",
            timeout_seconds=10,
            verification_methods=["content_hash", "read_back"],
            test_status="verified",
            reliability_score=0.99,
            source_file="lib/safe_gui_ctl.py",
            created_at=now,
            updated_at=now,
        ),
        
        # ===== CLI-Anything placeholder =====
        ToolContract(
            tool_id="cli_anything.obs_studio",
            name="OBS Studio CLI",
            description="OBS Studio CLI adapter (via CLI-Anything)",
            capabilities=[CapabilityCategory.LAUNCH, CapabilityCategory.INTERACT, CapabilityCategory.INSPECT],
            backend=BackendType.CLI_ANYTHING,
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object"},
            supported_applications=["obs-studio"],
            risk_level="low",
            timeout_seconds=30,
            verification_methods=["json_output", "status_check"],
            test_status="untested",
            reliability_score=0.0,
            source_file="lib/cli_anything_adapter.py",
            created_at=now,
            updated_at=now,
        ),
    ]
    
    return contracts


if __name__ == "__main__":
    # Create registry and register default contracts
    registry = CapabilityRegistry()
    
    contracts = create_default_contracts()
    for contract in contracts:
        registry.register(contract)
    
    print(f"\n=== Registry Summary ===")
    print(f"Total tools: {len(registry.tools)}")
    
    for backend in BackendType:
        tools = registry.list_by_backend(backend)
        if tools:
            print(f"  {backend.value}: {len(tools)} tools")
    
    for cap in CapabilityCategory:
        tools = registry.list_by_capability(cap)
        if tools:
            print(f"  {cap.value}: {len(tools)} tools")
    
    print("\nRegistry initialized successfully!")