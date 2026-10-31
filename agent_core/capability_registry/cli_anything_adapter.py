"""
CLI-Anything Adapter - Integrates CLI-Anything generated CLIs with the Capability Registry.
"""
from __future__ import annotations
import subprocess
import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

from capability_registry.registry import ToolContract, CapabilityRegistry, CapabilityCategory, BackendType


@dataclass
class CLIAdapterInfo:
    """Information about a CLI-Anything adapter."""
    tool_id: str
    cli_name: str
    executable: str
    capabilities: List[str]
    version: str = "1.0.0"
    install_method: str = "cli-hub"


class CLIAnythingAdapter:
    """Manages CLI-Anything adapters and integrates them with the capability registry."""
    
    def __init__(self, registry: CapabilityRegistry, hub_path: Optional[str] = None):
        self.registry = registry
        self.hub_path = hub_path or "cli-hub"
        self.adapters: Dict[str, CLIAdapterInfo] = {}
        self._cache_path = Path("C:/agent-work/agent_core/capability_registry/cli_anything_cache.json")
        self._load_cache()
    
    def _load_cache(self):
        """Load cached adapter information."""
        if self._cache_path.exists():
            try:
                with open(self._cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for tool_id, info in data.items():
                    self.adapters[tool_id] = CLIAdapterInfo(**info)
            except Exception as e:
                print(f"Failed to load CLI adapter cache: {e}")
    
    def _save_cache(self):
        """Save adapter cache."""
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: v.__dict__ for k, v in self.adapters.items()}
        with open(self._cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def is_available(self) -> bool:
        """Check if CLI-Anything hub is available."""
        try:
            result = subprocess.run(
                [self.hub_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def list_available(self) -> List[Dict[str, Any]]:
        """List available adapters from CLI-Hub."""
        if not self.is_available():
            return []
        
        try:
            result = subprocess.run(
                [self.hub_path, "list", "--json"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return json.loads(result.stdout)
        except Exception as e:
            print(f"Failed to list CLI-Hub adapters: {e}")
        return []
    
    def install_adapter(self, app_name: str) -> bool:
        """Install a CLI adapter for the given application."""
        if not self.is_available():
            print("CLI-Hub not available")
            return False
        
        try:
            result = subprocess.run(
                [self.hub_path, "install", app_name],
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode == 0:
                print(f"Installed CLI adapter for {app_name}")
                self._refresh_adapter(app_name)
                return True
            else:
                print(f"Failed to install {app_name}: {result.stderr}")
                return False
        except Exception as e:
            print(f"Error installing {app_name}: {e}")
            return False
    
    def _refresh_adapter(self, app_name: str):
        """Refresh adapter info after installation."""
        try:
            # Get the entry point from hub list
            available = self.list_available()
            adapter_info = None
            for a in available:
                if a.get('name') == app_name:
                    adapter_info = a
                    break
            
            if not adapter_info:
                print(f"Adapter {app_name} not found in hub list")
                return
            
            entry_point = adapter_info.get('entry_point', '')
            if not entry_point:
                # Try to derive from name
                entry_point = f"cli-anything-{app_name}"
            
            # Test the executable
            try:
                result = subprocess.run(
                    [entry_point, "--help"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    capabilities = self._parse_help_for_capabilities(result.stdout)
                    
                    # Use entry_point as tool_id (replace hyphens with underscores for tool_id)
                    tool_id = entry_point.replace('-', '_').replace('.', '_')
                    
                    info = CLIAdapterInfo(
                        tool_id=tool_id,
                        cli_name=entry_point,
                        executable=entry_point,
                        capabilities=capabilities,
                    )
                    self.adapters[tool_id] = info
                    self._save_cache()
                    
                    # Register with capability registry
                    self._register_with_registry(info)
                    print(f"Refreshed adapter: {tool_id}")
            except Exception as e:
                print(f"Failed to test adapter {entry_point}: {e}")
        except Exception as e:
            print(f"Failed to refresh adapter for {app_name}: {e}")
    
    def _parse_help_for_capabilities(self, help_text: str) -> List[str]:
        """Parse CLI help text to extract capabilities."""
        capabilities = []
        text_lower = help_text.lower()
        
        capability_keywords = {
            "launch": ["start", "run", "launch", "open"],
            "capture": ["capture", "screenshot", "record", "stream"],
            "inspect": ["list", "show", "info", "status", "get"],
            "interact": ["click", "type", "input", "send", "control"],
            "verify": ["verify", "check", "validate", "assert"],
            "file_ops": ["read", "write", "copy", "move", "delete", "file"],
        }
        
        for cap, keywords in capability_keywords.items():
            if any(kw in text_lower for kw in keywords):
                capabilities.append(cap)
        
        return capabilities if capabilities else ["inspect"]
    
    def _register_with_registry(self, info: CLIAdapterInfo):
        """Register CLI adapter with capability registry."""
        # Create tool contract
        contract = ToolContract(
            tool_id=info.tool_id,
            name=f"{info.cli_name} CLI",
            description=f"CLI-Anything adapter for {info.cli_name}",
            version=info.version,
            capabilities=[c for c in info.capabilities],
            backend=BackendType.CLI_ANYTHING,
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object"},
            supported_applications=[info.cli_name],
            risk_level="low",
            timeout_seconds=30,
            verification_methods=["json_output", "exit_code"],
            test_status="untested",
            reliability_score=0.0,
            source_file="lib/cli_anything_adapter.py",
        )
        self.registry.register(contract)
        print(f"Registered CLI adapter: {info.tool_id}")
    
    def get_adapter(self, tool_id: str) -> Optional[CLIAdapterInfo]:
        """Get adapter info by tool ID."""
        return self.adapters.get(tool_id)
    
    def execute(self, tool_id: str, command: str, args: List[str] = None, 
                input_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute a CLI-Anything adapter command."""
        # Try exact match first
        adapter = self.adapters.get(tool_id)
        
        # If not found, try to find by entry_point
        if not adapter:
            for aid, ad in self.adapters.items():
                if ad.executable == tool_id or ad.tool_id == tool_id:
                    adapter = ad
                    break
        
        if not adapter:
            # Try to find by CLI-Anything naming convention
            # tool_id like "cli_anything.obs_studio" -> executable "cli-anything-obs-studio"
            executable = tool_id.replace('_', '-')
            for aid, ad in self.adapters.items():
                if ad.executable == executable:
                    adapter = ad
                    break
        
        if not adapter:
            return {"success": False, "error": f"Adapter not found: {tool_id}"}
        
        cmd = [adapter.executable, command]
        if args:
            cmd.extend(args)
        
        if input_data:
            # Pass input as JSON via stdin
            input_json = json.dumps(input_data)
        else:
            input_json = None
        
        try:
            result = subprocess.run(
                cmd,
                input=input_json,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            output = {}
            if result.stdout:
                try:
                    output = json.loads(result.stdout)
                except json.JSONDecodeError:
                    output = {"raw_output": result.stdout}
            
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "output": output,
                "stderr": result.stderr if result.stderr else None,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}


def demo_cli_anything():
    """Demonstrate CLI-Anything adapter (if available)."""
    from capability_registry.registry import CapabilityRegistry
    
    registry = CapabilityRegistry()
    adapter = CLIAnythingAdapter(registry)
    
    print("=== CLI-Anything Adapter Demo ===\n")
    
    if adapter.is_available():
        print("CLI-Hub is available!")
        available = adapter.list_available()
        print(f"Available adapters: {len(available)}")
        for a in available[:10]:
            print(f"  - {a.get('name', 'unknown')}: {a.get('description', 'no description')}")
        
        # Try to install OBS Studio adapter as pilot
        print("\nInstalling OBS Studio adapter...")
        if adapter.install_adapter("obs-studio"):
            print("OBS Studio adapter installed successfully!")
        else:
            print("OBS Studio adapter installation failed or not available")
    else:
        print("CLI-Hub not available. Install with: pip install cli-anything-hub")
        print("Skipping CLI-Anything integration for now.")


if __name__ == "__main__":
    demo_cli_anything()