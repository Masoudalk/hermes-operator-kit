"""
Tool Selector - Chooses the best available tool for a given task.
Evaluates reliability, latency, resource consumption, permissions, side effects,
observability, recoverability, and application compatibility.
"""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from pathlib import Path

from capability_registry.registry import (
    CapabilityRegistry, ToolContract, BackendType, CapabilityCategory
)


class SelectionReason(Enum):
    """Reasons for tool selection/rejection."""
    BEST_RELIABILITY = "best_reliability"
    LOWEST_LATENCY = "lowest_latency"
    LOWEST_RESOURCE = "lowest_resource"
    LEAST_SIDE_EFFECTS = "least_side_effects"
    BEST_OBSERVABILITY = "best_observability"
    BEST_RECOVERABILITY = "best_recoverability"
    APP_COMPATIBLE = "app_compatible"
    PERMISSION_OK = "permission_ok"
    FALLBACK = "fallback"
    
    # Rejection reasons
    INSUFFICIENT_RELIABILITY = "insufficient_reliability"
    EXCEEDS_LATENCY_BUDGET = "exceeds_latency_budget"
    EXCEEDS_RESOURCE_BUDGET = "exceeds_resource_budget"
    UNACCEPTABLE_SIDE_EFFECTS = "unacceptable_side_effects"
    INSUFFICIENT_OBSERVABILITY = "insufficient_observability"
    INSUFFICIENT_RECOVERABILITY = "insufficient_recoverability"
    APP_INCOMPATIBLE = "app_incompatible"
    PERMISSION_DENIED = "permission_denied"
    UNTESTED = "untested"
    DEPENDENCY_MISSING = "dependency_missing"


@dataclass
class SelectionContext:
    """Context for tool selection."""
    task_description: str
    required_capabilities: List[str] = field(default_factory=list)
    target_application: Optional[str] = None
    max_latency_ms: Optional[int] = None
    max_memory_mb: Optional[int] = None
    allowed_risk_levels: List[str] = field(default_factory=lambda: ["low", "medium"])
    required_permissions: List[str] = field(default_factory=list)
    forbidden_side_effects: List[str] = field(default_factory=list)
    require_verification: bool = True
    require_rollback: bool = False
    platform: str = "windows"


@dataclass
class ScoredTool:
    """A tool with its selection score and reasoning."""
    tool: Any  # ToolContract
    score: float
    reasons: List[SelectionReason] = field(default_factory=list)
    rejected_reasons: List[SelectionReason] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ToolSelector:
    """Selects the best tool for a given task based on multiple criteria."""
    
    def __init__(self, registry: CapabilityRegistry, config_path: Optional[str] = None):
        self.registry = registry
        self.config_path = config_path or "C:/agent-work/agent_core/capability_registry/selector_config.json"
        self.config = self._load_config()
        self._selection_history: List[Dict[str, Any]] = []
    
    def _load_config(self) -> Dict[str, Any]:
        """Load selector configuration."""
        path = Path(self.config_path)
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Failed to load selector config: {e}")
        
        # Default configuration
        return {
            "weights": {
                "reliability": 0.30,
                "latency": 0.20,
                "resource": 0.15,
                "side_effects": 0.15,
                "observability": 0.10,
                "recoverability": 0.10,
            },
            "thresholds": {
                "min_reliability": 0.70,
                "max_latency_ms": 30000,
                "max_memory_mb": 500,
                "min_observability": 0.50,
                "min_recoverability": 0.50,
            },
            "risk_levels": {
                "low": 1.0,
                "medium": 0.7,
                "high": 0.3,
                "critical": 0.1,
            },
            "backend_preference": [
                "native_cli",
                "cli_anything",
                "windows_uia",
                "desktop_bridge",
                "api",
                "mcp",
                "browser_cdp",
                "browser_dom",
                "mouse_keyboard",
                "screenshot_vision",
                "ocr",
                "filesystem",
            ],
        }
    
    def save_config(self):
        """Save selector configuration."""
        path = Path(self.config_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def select_tool(self, context: SelectionContext) -> Tuple[Optional[Any], Dict[str, Any]]:
        """
        Select the best tool for the given context.
        Returns (selected_tool, selection_metadata).
        """
        # Get candidate tools
        candidates = self._get_candidates(context)
        
        if not candidates:
            return None, {
                "selected": False,
                "reason": "No compatible tools found",
                "candidates_evaluated": 0,
                "rejected": []
            }
        
        # Score each candidate
        scored = [self._score_tool(tool, context) for tool in candidates]
        
        # Filter out rejected tools
        viable = [s for s in scored if not s.rejected_reasons]
        
        if not viable:
            return None, {
                "selected": False,
                "reason": "All candidates rejected",
                "candidates_evaluated": len(candidates),
                "rejected": [
                    {
                        "tool_id": s.tool.tool_id,
                        "reasons": [r.value for r in s.rejected_reasons]
                    }
                    for s in scored
                ]
            }
        
        # Sort by score (highest first)
        viable.sort(key=lambda s: s.score, reverse=True)
        
        selected = viable[0]
        
        # Record selection
        selection_record = {
            "timestamp": __import__('datetime').datetime.now().isoformat(),
            "context": {
                "task": context.task_description,
                "capabilities": context.required_capabilities,
                "app": context.target_application,
            },
            "selected_tool": selected.tool.tool_id,
            "score": selected.score,
            "reasons": [r.value for r in selected.reasons],
            "alternatives": [
                {"tool_id": s.tool.tool_id, "score": s.score}
                for s in viable[1:4]
            ],
        }
        self._selection_history.append(selection_record)
        
        return selected.tool, {
            "selected": True,
            "tool_id": selected.tool.tool_id,
            "score": selected.score,
            "reasons": [r.value for r in selected.reasons],
            "alternatives": [
                {"tool_id": s.tool.tool_id, "score": s.score}
                for s in viable[1:4]
            ],
            "candidates_evaluated": len(candidates),
            "rejected": [
                {
                    "tool_id": s.tool.tool_id,
                    "reasons": [r.value for r in s.rejected_reasons]
                }
                for s in scored if s.rejected_reasons
            ],
        }
    
    def _get_candidates(self, context: SelectionContext) -> List[Any]:
        """Get candidate tools that match basic requirements."""
        candidates = []
        
        for tool in self.registry.list_all():
            # Check capability match
            if context.required_capabilities:
                tool_caps = [c.value for c in tool.capabilities]
                if not all(cap in tool_caps for cap in context.required_capabilities):
                    continue
            
            # Check application compatibility
            if context.target_application:
                supported = tool.supported_applications
                if supported and context.target_application.lower() not in [a.lower() for a in supported]:
                    continue
            
            # Check platform
            if context.platform not in tool.platform:
                continue
            
            # Check risk level
            if tool.risk_level not in context.allowed_risk_levels:
                continue
            
            # Check permissions
            if context.required_permissions:
                if not all(p in tool.permissions for p in context.required_permissions):
                    continue
            
            # Check forbidden side effects
            if context.forbidden_side_effects:
                tool_side_effects = self._get_side_effects(tool)
                if any(e in tool_side_effects for e in context.forbidden_side_effects):
                    continue
            
            # Check verification requirement
            if context.require_verification and not tool.verification_methods:
                continue
            
            # Check rollback requirement
            if context.require_rollback and not tool.rollback_capable:
                continue
            
            candidates.append(tool)
        
        return candidates
    
    def _get_side_effects(self, tool: Any) -> List[str]:
        """Get side effects for a tool based on its capabilities and risk."""
        effects = []
        if tool.risk_level in ["medium", "high", "critical"]:
            effects.append("state_change")
        if CapabilityCategory.INTERACT in tool.capabilities:
            effects.append("ui_interaction")
        if CapabilityCategory.LAUNCH in tool.capabilities:
            effects.append("process_creation")
        if CapabilityCategory.FILE_OPS in tool.capabilities:
            effects.append("filesystem_write")
        if tool.backend in [BackendType.MOUSE_KEYBOARD, BackendType.DESKTOP_BRIDGE]:
            effects.append("ui_interaction")
        return effects
    
    def _score_tool(self, tool: Any, context: SelectionContext) -> Any:
        """Score a tool based on multiple criteria."""
        from capability_registry.registry import ToolContract
        
        # Create scored tool object
        scored = type('ScoredTool', (), {
            'tool': tool,
            'score': 0.0,
            'reasons': [],
            'rejected_reasons': [],
            'metadata': {}
        })()
        
        weights = self.config.get("weights", {})
        thresholds = self.config.get("thresholds", {})
        risk_weights = self.config.get("risk_levels", {})
        backend_pref = self.config.get("backend_preference", [])
        
        # --- Reliability Score ---
        reliability = tool.reliability_score
        min_reliability = thresholds.get("min_reliability", 0.70)
        
        if reliability < min_reliability:
            scored.rejected_reasons.append(SelectionReason.INSUFFICIENT_RELIABILITY)
            return scored
        
        scored.score += reliability * weights.get("reliability", 0.30)
        if reliability > 0.9:
            scored.reasons.append(SelectionReason.BEST_RELIABILITY)
        
        # --- Latency Score ---
        latency_score = 1.0 - min(tool.timeout_seconds / 300.0, 1.0)  # Normalize to 5 min max
        max_latency = thresholds.get("max_latency_ms", 30000) / 1000.0  # Convert to seconds
        if tool.timeout_seconds > max_latency:
            scored.rejected_reasons.append(SelectionReason.EXCEEDS_LATENCY_BUDGET)
            return scored
        
        scored.score += latency_score * weights.get("latency", 0.20)
        if tool.timeout_seconds < 10:
            scored.reasons.append(SelectionReason.LOWEST_LATENCY)
        
        # --- Resource Score ---
        resource_score = 1.0  # Default, would be refined with actual metrics
        max_memory = thresholds.get("max_memory_mb", 500)
        # Assume tools use minimal memory unless known otherwise
        scored.score += resource_score * weights.get("resource", 0.15)
        
        # --- Side Effects Score ---
        side_effects = self._get_side_effects(tool)
        side_effect_penalty = len([e for e in side_effects if e in ["state_change", "filesystem_write", "process_creation"]]) * 0.1
        side_effect_score = max(0.0, 1.0 - side_effect_penalty)
        
        if context.forbidden_side_effects and any(e in side_effects for e in context.forbidden_side_effects):
            scored.rejected_reasons.append(SelectionReason.UNACCEPTABLE_SIDE_EFFECTS)
            return scored
        
        scored.score += side_effect_score * weights.get("side_effects", 0.15)
        if not side_effects:
            scored.reasons.append(SelectionReason.LEAST_SIDE_EFFECTS)
        
        # --- Observability Score ---
        observability = len(tool.verification_methods) / 3.0  # Normalize to max 3 methods
        min_obs = thresholds.get("min_observability", 0.50)
        
        if observability < min_obs and context.require_verification:
            scored.rejected_reasons.append(SelectionReason.INSUFFICIENT_OBSERVABILITY)
            return scored
        
        scored.score += observability * weights.get("observability", 0.10)
        if observability > 0.8:
            scored.reasons.append(SelectionReason.BEST_OBSERVABILITY)
        
        # --- Recoverability Score ---
        recoverability = 1.0 if tool.rollback_capable else 0.3
        if tool.idempotent:
            recoverability = 1.0
        
        min_rec = thresholds.get("min_recoverability", 0.50)
        if recoverability < min_rec and context.require_rollback:
            scored.rejected_reasons.append(SelectionReason.INSUFFICIENT_RECOVERABILITY)
            return scored
        
        scored.score += recoverability * weights.get("recoverability", 0.10)
        if recoverability > 0.8:
            scored.reasons.append(SelectionReason.BEST_RECOVERABILITY)
        
        # --- Application Compatibility ---
        if context.target_application:
            supported = tool.supported_applications
            if supported and context.target_application.lower() not in [a.lower() for a in supported]:
                scored.rejected_reasons.append(SelectionReason.APP_INCOMPATIBLE)
                return scored
            scored.reasons.append(SelectionReason.APP_COMPATIBLE)
        
        # --- Permission Check ---
        if context.required_permissions:
            if not all(p in tool.permissions for p in context.required_permissions):
                scored.rejected_reasons.append(SelectionReason.PERMISSION_DENIED)
                return scored
            scored.reasons.append(SelectionReason.PERMISSION_OK)
        
        # --- Backend Preference ---
        try:
            backend_idx = self.config["backend_preference"].index(tool.backend.value)
            backend_score = 1.0 - (backend_idx / len(self.config["backend_preference"]))
            scored.score += backend_score * 0.05  # Small bonus for preferred backend
        except ValueError:
            pass
        
        # --- Risk Level Weight ---
        risk_weight = risk_weights.get(tool.risk_level, 0.5)
        scored.score *= risk_weight
        
        # --- Test Status ---
        if tool.test_status == "untested":
            scored.score *= 0.5
            scored.rejected_reasons.append(SelectionReason.UNTESTED)
            return scored
        elif tool.test_status == "partial":
            scored.score *= 0.8
        
        # Ensure score is in valid range
        scored.score = max(0.0, min(1.0, scored.score))
        
        return scored
    
    def get_selection_history(self) -> List[Dict[str, Any]]:
        """Get selection history."""
        return self._selection_history.copy()
    
    def explain_selection(self, tool_id: str, context: SelectionContext) -> Dict[str, Any]:
        """Explain why a tool was selected or rejected."""
        tool = self.registry.get(tool_id)
        if not tool:
            return {"error": "Tool not found"}
        
        scored = self._score_tool(tool, context)
        
        return {
            "tool_id": tool_id,
            "selected": not scored.rejected_reasons,
            "score": scored.score,
            "reasons": [r.value for r in scored.reasons],
            "rejected_reasons": [r.value for r in scored.rejected_reasons],
            "metadata": scored.metadata,
        }


def demo_selector():
    """Demonstrate the tool selector."""
    from capability_registry.registry import CapabilityRegistry
    
    registry = CapabilityRegistry()
    selector = ToolSelector(registry)
    
    # Test selection for various tasks
    contexts = [
        SelectionContext(
            task_description="Launch Notepad and type 'Hello World'",
            required_capabilities=["launch", "interact", "verify"],
            target_application="notepad.exe",
            require_verification=True,
        ),
        SelectionContext(
            task_description="Capture current desktop screenshot",
            required_capabilities=["capture", "verify"],
            require_verification=True,
        ),
        SelectionContext(
            task_description="Get list of all open windows",
            required_capabilities=["inspect"],
            target_application=None,
        ),
        SelectionContext(
            task_description="Focus the Notepad window",
            required_capabilities=["interact"],
            target_application="notepad.exe",
        ),
        SelectionContext(
            task_description="Read a text file",
            required_capabilities=["file_ops"],
        ),
    ]
    
    print("=== Tool Selection Demo ===\n")
    
    for i, context in enumerate(contexts, 1):
        print(f"--- Task {i}: {context.task_description} ---")
        tool, metadata = selector.select_tool(context)
        
        if tool:
            print(f"  Selected: {tool.tool_id} (score: {metadata['score']:.3f})")
            print(f"  Reasons: {', '.join(metadata['reasons'])}")
            if metadata['alternatives']:
                print(f"  Alternatives: {', '.join([a['tool_id'] for a in metadata['alternatives']])}")
        else:
            print(f"  No tool selected: {metadata['reason']}")
        print()


if __name__ == "__main__":
    demo_selector()