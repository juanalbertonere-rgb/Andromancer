from __future__ import annotations
import asyncio
import subprocess
import inspect
from abc import ABC, abstractmethod
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable, Callable
from concurrent.futures import ThreadPoolExecutor
from andromancer.utils.adb import adb_manager

logger = logging.getLogger("AndroMancer.Capabilities")

@dataclass
class ExecutionResult:
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0

@runtime_checkable
class Capability(Protocol):
    name: str
    description: str
    risk_level: str

    async def execute(self, **params) -> ExecutionResult:
        ...

class ADBCapability:
    """Base class for ADB-based capabilities"""
    async def _adb(self, cmd: List[str], timeout: int = 15) -> subprocess.CompletedProcess:
        await adb_manager.ensure_connected()
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as pool:
            return await loop.run_in_executor(
                pool,
                lambda: subprocess.run(
                    ["adb"] + cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
            )

class CapabilityRegistry:
    """Registry for capabilities"""
    def __init__(self):
        self._capabilities: Dict[str, Capability] = {}
        self.safety_check_callback: Optional[Callable[[str, Dict, Dict], Coroutine]] = None

    def register(self, capability: Capability):
        self._capabilities[capability.name] = capability
        logger.info(f"Capability registered: {capability.name}")

    def get(self, name: str) -> Optional[Capability]:
        return self._capabilities.get(name)

    def list_capabilities(self) -> List[Dict]:
        return [
            {
                "name": cap.name,
                "description": cap.description,
                "risk": cap.risk_level,
                "parameters": self._get_cap_params(cap)
            }
            for cap in self._capabilities.values()
        ]

    def _get_cap_params(self, cap: Capability) -> Dict[str, str]:
        sig = inspect.signature(cap.execute)
        params = {}
        for name, param in sig.parameters.items():
            if name in ['self', 'kwargs']:
                continue

            # Get type hint if available
            type_name = "any"
            if param.annotation != inspect.Parameter.empty:
                if hasattr(param.annotation, '__name__'):
                    type_name = param.annotation.__name__
                else:
                    type_name = str(param.annotation).replace('typing.', '')

            # Indicate if optional
            suffix = ""
            if param.default != inspect.Parameter.empty:
                suffix = f" (optional, default: {param.default})"

            params[name] = f"{type_name}{suffix}"
        return params

    async def execute(self, name: str, params: Dict, context: Dict = None) -> ExecutionResult:
        cap = self._capabilities.get(name)
        if not cap:
            return ExecutionResult(False, error=f"Unknown capability: {name}")

        if cap.risk_level in ["high", "critical"] and self.safety_check_callback:
            approved = await self.safety_check_callback(name, params, context or {})
            if not approved:
                return ExecutionResult(False, error="Safety check failed or rejected")

        start = time.time()
        try:
            result = await cap.execute(**params)
            result.execution_time = time.time() - start
            return result
        except Exception as e:
            return ExecutionResult(False, error=str(e), execution_time=time.time()-start)
