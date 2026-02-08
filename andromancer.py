#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AndroMancer v11.0 - "Agent-First Architecture"
Sistema autónomo Android basado en Agent Architecture con:
- ReAct Reasoning Loop (Reasoning + Acting)
- Vector Memory para UI states históricos
- Capability Registry dinámico
- Parallel Action Execution
- Observability completa
"""
from __future__ import annotations

import os
import sys
import time
import json
import re
import asyncio
import hashlib
import shlex
import tempfile
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import (
    Any, Callable, Coroutine, Dict, Generic, List, Optional,
    Protocol, Set, TypeVar, Union, runtime_checkable, Tuple
)
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import xml.etree.ElementTree as ET
import subprocess

# Configuration with Pydantic-style validation
try:
    import settings as cfg
except Exception:
    class Config:
        GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
        MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")
        MAX_STEPS = 20
        ADB_TIMEOUT = 15
        STATE_DIR = Path.home() / ".andromancer"
        VECTOR_DB_PATH = STATE_DIR / "memory.vec"
        LOG_LEVEL = "INFO"
        AUTONOMY_LEVEL = "full"
        CONFIDENCE_THRESHOLD = 0.75
        PARALLEL_ACTIONS = True
        SAFETY_CHECKPOINTS = True
    cfg = Config()

# Ensure directories exist
cfg.STATE_DIR.mkdir(parents=True, exist_ok=True)

# Setup structured logging
logging.basicConfig(
    level=getattr(logging, cfg.LOG_LEVEL),
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    handlers=[
        logging.FileHandler(cfg.STATE_DIR / "agent.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AndroMancer")

# -----------------------------------------------------------------------------
# SYSTEM PROMPT (REACT)
# -----------------------------------------------------------------------------
REACT_SYSTEM_PROMPT = """You are AndroMancer, an autonomous Android agent.

## Your Capabilities
{capabilities_json}

## Reasoning Protocol (ReAct)
For each step, think in this format:

**Thought**: Analyze current state and decide next action
**Action**: Choose ONE capability to execute
**Params**: JSON parameters for the capability
**Confidence**: 0.0-1.0 how sure you are

## Output Format (JSON)
{{
    "reasoning": "step-by-step analysis of current situation",
    "action_plan": [
        {{
            "capability": "capability_name",
            "params": {{"param_key": "param_value"}},
            "expected_outcome": "what should happen",
            "critical": false,
            "async": false,
            "depends_on": null
        }}
    ],
    "confidence": 0.85,
    "next_steps": "what to do after this action succeeds"
}}

## Rules
1. ALWAYS analyze UI state before acting
2. If action fails, try alternative approach (don't repeat same action)
3. Use memory of past experiences
4. Ask for help if stuck after 3 failed attempts
5. NEVER execute high-risk actions without confirmation

## Current Context
Goal: {goal}
Step: {step}/{max_steps}
Previous actions: {action_history}
Relevant memories: {memories}
"""

# -----------------------------------------------------------------------------
# CORE AGENT ARCHITECTURE
# -----------------------------------------------------------------------------

class EventType(Enum):
    THOUGHT = auto()
    ACTION = auto()
    OBSERVATION = auto()
    REFLECTION = auto()
    ERROR = auto()
    COMPLETION = auto()
    SAFETY_CHECK = auto()

@dataclass
class AgentEvent:
    timestamp: float
    type: EventType
    content: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

class EventBus:
    """Sistema de eventos desacoplado para observabilidad"""
    def __init__(self):
        self._handlers: List[Callable[[AgentEvent], Coroutine]] = []
        self._history: deque = deque(maxlen=1000)

    def subscribe(self, handler: Callable[[AgentEvent], Coroutine]):
        self._handlers.append(handler)

    async def emit(self, event: AgentEvent):
        self._history.append(event)
        for handler in self._handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Event handler error: {e}")

event_bus = EventBus()

# -----------------------------------------------------------------------------
# MEMORY SYSTEM (Vector + Episódica + Procedural)
# -----------------------------------------------------------------------------

@dataclass
class Memory:
    id: str
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    access_count: int = 0
    last_access: float = field(default_factory=time.time)

class MemoryStore:
    """Memoria semántica con embeddings simples (simulado con hash vectors para MVP)"""
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.memories: List[Memory] = []
        self._load()

    def _hash_embedding(self, text: str) -> List[float]:
        """Simulación de embedding con hash distribuido"""
        hash_obj = hashlib.md5(text.encode())
        hash_int = int(hash_obj.hexdigest(), 16)
        vec = [((hash_int >> (i * 4)) & 0xF) / 16.0 for i in range(16)]
        return vec

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        dot = sum(x*y for x,y in zip(a,b))
        norm_a = sum(x*x for x in a) ** 0.5
        norm_b = sum(x*x for x in b) ** 0.5
        return dot / (norm_a * norm_b) if norm_a * norm_b else 0

    def store(self, content: str, metadata: Dict = None) -> Memory:
        mem = Memory(
            id=hashlib.md5(f"{content}{time.time()}".encode()).hexdigest()[:12],
            content=content,
            embedding=self._hash_embedding(content),
            metadata=metadata or {}
        )
        self.memories.append(mem)
        self._save()
        return mem

    def retrieve(self, query: str, top_k: int = 5) -> List[Memory]:
        if not self.memories:
            return []
        query_vec = self._hash_embedding(query)
        scored = []
        for mem in self.memories:
            sim = self._cosine_similarity(query_vec, mem.embedding)
            scored.append((sim, mem))
        scored.sort(key=lambda x: x[0], reverse=True)
        results = [m for _, m in scored[:top_k]]
        for m in results:
            m.access_count += 1
            m.last_access = time.time()
        return results

    def _save(self):
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, 'w') as f:
                json.dump([asdict(m) for m in self.memories], f)
        except Exception as e:
            logger.error(f"Memory save error: {e}")

    def _load(self):
        if self.storage_path.exists():
            try:
                with open(self.storage_path) as f:
                    data = json.load(f)
                    self.memories = [Memory(**m) for m in data]
            except Exception as e:
                logger.error(f"Memory load error: {e}")

memory = MemoryStore(cfg.VECTOR_DB_PATH)

# -----------------------------------------------------------------------------
# CAPABILITY SYSTEM (Herramientas dinámicas)
# -----------------------------------------------------------------------------

T = TypeVar('T')

@runtime_checkable
class Capability(Protocol):
    """Protocolo para capacidades del agente"""
    name: str
    description: str
    risk_level: str

    async def execute(self, **params) -> ExecutionResult:
        ...

@dataclass
class ExecutionResult:
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0

class CapabilityRegistry:
    """Registro dinámico de capacidades (Tools/Functions)"""
    def __init__(self):
        self._capabilities: Dict[str, Capability] = {}
        self._safety_hooks: Dict[str, Callable] = {}

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
                "risk": cap.risk_level
            }
            for cap in self._capabilities.values()
        ]

    async def execute(self, name: str, params: Dict, context: Dict) -> ExecutionResult:
        cap = self._capabilities.get(name)
        if not cap:
            return ExecutionResult(False, error=f"Unknown capability: {name}")

        if cap.risk_level in ["high", "critical"]:
            approved = await self._check_safety(name, params, context)
            if not approved:
                return ExecutionResult(False, error="Safety check failed")

        start = time.time()
        try:
            result = await cap.execute(**params)
            result.execution_time = time.time() - start
            return result
        except Exception as e:
            return ExecutionResult(False, error=str(e), execution_time=time.time()-start)

    async def _check_safety(self, name: str, params: Dict, context: Dict) -> bool:
        await event_bus.emit(AgentEvent(
            time.time(), EventType.SAFETY_CHECK,
            {"capability": name, "params": params}
        ))
        return True

registry = CapabilityRegistry()

# -----------------------------------------------------------------------------
# ADB MANAGER & CAPABILITIES
# -----------------------------------------------------------------------------

class ADBConnectionError(Exception):
    pass

class ADBManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
            cls._instance.device_id = None
        return cls._instance

    async def _run(self, cmd: List[str], timeout: int = 15) -> subprocess.CompletedProcess:
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as pool:
            return await loop.run_in_executor(
                pool,
                lambda: subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
            )

    async def ensure_connected(self) -> bool:
        if getattr(self, "_initialized", False):
            return True

        try:
            result = await self._run(["adb", "devices"], timeout=cfg.ADB_TIMEOUT)
            out = (result.stdout or "") + (result.stderr or "")
            devices = [l for l in out.splitlines() if "\tdevice" in l and not l.startswith("List of devices")]
            if not devices:
                raise ADBConnectionError("No Android device connected")
            first_device_line = devices[0].strip()
            self.device_id = first_device_line.split()[0]
            self._initialized = True
            logger.info(f"ADB connected: {self.device_id}")
            return True
        except Exception as e:
            logger.error(f"ADB ensure_connected error: {e}")
            raise ADBConnectionError(str(e))

adb_manager = ADBManager()

class ADBCapability:
    """Base para capacidades ADB"""
    def __init__(self):
        self.device_id: Optional[str] = None
        self._connected = False
        self._cache: Dict = {}

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

class TapCapability(ADBCapability, Capability):
    name = "tap"
    description = "Toca en coordenadas (x, y) o en elemento UI"
    risk_level = "low"

    async def execute(self, x: Optional[int] = None, y: Optional[int] = None,
                     element: Optional[Dict] = None) -> ExecutionResult:
        if element:
            bounds = element.get('bounds', '')
            nums = [int(n) for n in re.findall(r"-?\d+", bounds)]
            if len(nums) >= 4:
                x, y = (nums[0] + nums[2]) // 2, (nums[1] + nums[3]) // 2

        if x is None or y is None:
            return ExecutionResult(False, error="Coordinates required")

        result = await self._adb(["shell", "input", "tap", str(x), str(y)])
        success = result.returncode == 0
        return ExecutionResult(success, data={"x": x, "y": y}, error=None if success else result.stderr)

class UIScrapeCapability(ADBCapability, Capability):
    name = "get_ui"
    description = "Obtiene jerarquía UI actual como XML estructurado"
    risk_level = "low"

    async def execute(self, use_cache: bool = False) -> ExecutionResult:
        try:
            temp_dir = Path(tempfile.gettempdir())
            
            if not os.access("/tmp", os.W_OK):
                temp_dir = Path.home() / ".cache" / "andromancer"
            
            temp_dir.mkdir(parents=True, exist_ok=True)
            local_ui_path = temp_dir / "ui.xml"
            
            await self._adb(["shell", "uiautomator", "dump", "/sdcard/ui.xml"])
            await asyncio.sleep(0.3)

            result = await self._adb(["pull", "/sdcard/ui.xml", str(local_ui_path)])
            if result.returncode != 0:
                return ExecutionResult(False, error="Failed to pull UI: " + (result.stderr or ""))

            try:
                with open(local_ui_path, "r", encoding="utf-8") as f:
                    xml_content = f.read()

                root = ET.fromstring(xml_content)
                elements = self._parse_nodes(root)

                screen_summary = self._summarize_screen(elements)
                memory.store(screen_summary, {"type": "screen", "elements_count": len(elements)})

                return ExecutionResult(True, data={
                    "xml": xml_content,
                    "elements": elements,
                    "summary": screen_summary
                })
            except Exception as e:
                return ExecutionResult(False, error=f"XML parse error: {str(e)}")
        except Exception as e:
            return ExecutionResult(False, error=f"UI scrape error: {str(e)}")

    def _parse_nodes(self, root) -> List[Dict]:
        elements = []
        for node in root.iter('node'):
            if node.get('clickable') == 'true':
                elements.append({
                    "text": node.get('text', ''),
                    "content_desc": node.get('content-desc', ''),
                    "resource_id": node.get('resource-id', ''),
                    "class": node.get('class', ''),
                    "bounds": node.get('bounds', ''),
                    "package": node.get('package', '')
                })
        return elements

    def _summarize_screen(self, elements: List[Dict]) -> str:
        texts = [e['text'] or e['content_desc'] for e in elements[:10] if e['text'] or e['content_desc']]
        return "Screen with: " + ", ".join(texts) if texts else "Screen with no visible text"

class TypeCapability(ADBCapability, Capability):
    name = "type"
    description = "Escribe texto en campo focalizado"
    risk_level = "medium"

    async def execute(self, text: str) -> ExecutionResult:
        safe_text = text.replace("'", "\\'").replace('"', '\\"').replace(" ", "%s")
        result = await self._adb(["shell", "input", "text", safe_text])
        success = result.returncode == 0
        return ExecutionResult(success, data={"text": text}, error=None if success else result.stderr)

class OpenAppCapability(ADBCapability, Capability):
    name = "open_app"
    description = "Abre aplicación por nombre o package"
    risk_level = "low"

    async def execute(self, app_name: str) -> ExecutionResult:
        app_map = {
            "whatsapp": "com.whatsapp",
            "chrome": "com.android.chrome",
            "home": "HOME",
            "settings": "com.android.settings",
            "instagram": "com.instagram.android",
            "twitter": "com.twitter.android",
            "gmail": "com.google.android.gm"
        }
        package = app_map.get(app_name.lower(), app_name)

        if package == "HOME":
            await self._adb(["shell", "input", "keyevent", "3"])
        else:
            result = await self._adb(["shell", "monkey", "-p", package, "1"])
            if result.returncode != 0:
                return ExecutionResult(False, error=f"Failed to open {package}: {result.stderr}")

        await asyncio.sleep(1.5)
        return ExecutionResult(True, data={"package": package})

class SwipeCapability(ADBCapability, Capability):
    name = "swipe"
    description = "Desliza desde (x1,y1) hasta (x2,y2) con duración en ms"
    risk_level = "low"

    async def execute(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> ExecutionResult:
        result = await self._adb(["shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration)])
        success = result.returncode == 0
        return ExecutionResult(success, data={"x1": x1, "y1": y1, "x2": x2, "y2": y2}, error=None if success else result.stderr)

class BackCapability(ADBCapability, Capability):
    name = "back"
    description = "Presiona el botón de retroceso"
    risk_level = "low"

    async def execute(self) -> ExecutionResult:
        result = await self._adb(["shell", "input", "keyevent", "4"])
        success = result.returncode == 0
        return ExecutionResult(success, data={"action": "back"}, error=None if success else result.stderr)

# Registrar capacidades
for cap_class in [TapCapability, UIScrapeCapability, TypeCapability, OpenAppCapability, SwipeCapability, BackCapability]:
    registry.register(cap_class())

# -----------------------------------------------------------------------------
# LLM CLIENT
# -----------------------------------------------------------------------------

class LLMError(Exception):
    pass

class AsyncLLMClient:
    """Cliente async para el LLM (GROQ/OpenAI chat completions)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or cfg.GROQ_API_KEY
        self.model = model or cfg.MODEL_NAME

    async def complete_chat(self, system_prompt: str, user_prompt: str, timeout: float = 30.0) -> dict:
        try:
            import httpx
        except ImportError:
            raise LLMError("httpx required for LLM client. Install: pip install httpx --break-system-packages")

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": 0.3,
                        "response_format": {"type": "json_object"}
                    },
                    timeout=timeout
                )
            
            if resp.status_code >= 400:
                raise LLMError(f"LLM request failed: {resp.status_code} {resp.text}")
            
            body = resp.json()
            content = body["choices"][0]["message"]["content"]
            
            if isinstance(content, str):
                return json.loads(content)
            elif isinstance(content, dict):
                return content
            else:
                raise LLMError("Unexpected LLM content format")
                
        except Exception as e:
            raise LLMError(f"Failed to call LLM: {str(e)}")

# -----------------------------------------------------------------------------
# REASONING ENGINE (ReAct Pattern)
# -----------------------------------------------------------------------------

@dataclass
class Thought:
    step: int
    reasoning: str
    action_plan: List[Dict]
    confidence: float
    reflection: Optional[str] = None

class ReActEngine:
    """Implementación de Reasoning + Acting con memoria de trabajo"""
    def __init__(self, llm_client: Optional[AsyncLLMClient] = None):
        self.llm = llm_client or AsyncLLMClient()
        self.thought_history: List[Thought] = []
        self.working_memory: Dict = {}

    async def reason(self, goal: str, observation: Dict, step: int) -> Thought:
        """Genera siguiente pensamiento basado en observación actual"""

        relevant_memories = memory.retrieve(f"{goal} {str(observation)}", top_k=3)
        memory_context = "\n".join([m.content for m in relevant_memories])

        user_prompt = f"""Goal: {goal}
Step: {step}
Previous thoughts: {len(self.thought_history)}
Working memory: {self.working_memory}

Recent memories:
{memory_context}

Current observation:
{json.dumps(observation, indent=2)}

Analyze the current state and decide next actions. Respond with JSON following the Output Format.
"""
        
        try:
            system_prompt = REACT_SYSTEM_PROMPT.format(
                capabilities_json=json.dumps(registry.list_capabilities(), indent=2),
                goal=goal,
                step=step,
                max_steps=cfg.MAX_STEPS,
                action_history=[t.action_plan for t in self.thought_history[-3:]],
                memories=memory_context
            )
            
            thought_data = await self.llm.complete_chat(system_prompt, user_prompt)

            reasoning = thought_data.get("reasoning", "No reasoning provided")
            action_plan = thought_data.get("action_plan", [])
            confidence = float(thought_data.get("confidence", 0.0))

            thought = Thought(
                step=step,
                reasoning=reasoning,
                action_plan=action_plan,
                confidence=confidence
            )
            
        except Exception as e:
            logger.warning(f"LLM call failed in reason(): {e}. Using fallback reasoning.")
            
            if step == 0:
                thought = Thought(
                    step=step,
                    reasoning="Starting mission, need to understand current UI state (fallback)",
                    action_plan=[{"capability": "get_ui", "params": {}, "async": False}],
                    confidence=0.9
                )
            elif observation.get("elements"):
                elements = observation.get("elements", [])
                if elements:
                    thought = Thought(
                        step=step,
                        reasoning="Found interactive elements, selecting first clickable (fallback)",
                        action_plan=[{"capability": "tap", "params": {"element": elements[0]}}],
                        confidence=0.6
                    )
                else:
                    thought = Thought(
                        step=step,
                        reasoning="No interactive elements found (fallback)",
                        action_plan=[],
                        confidence=0.5
                    )
            else:
                thought = Thought(
                    step=step,
                    reasoning="Task completed or needs user input (fallback)",
                    action_plan=[],
                    confidence=1.0
                )

        self.thought_history.append(thought)
        await event_bus.emit(AgentEvent(
            time.time(), EventType.THOUGHT,
            {"step": step, "reasoning": thought.reasoning, "confidence": thought.confidence}
        ))
        return thought

    async def reflect(self, thought: Thought, result: ExecutionResult) -> Thought:
        """Reflexión sobre el resultado de la acción"""
        try:
            action_desc = thought.action_plan[0] if thought.action_plan else {}
            prompt = f"""
Action executed: {action_desc.get('capability', 'unknown')}
Expected outcome: {action_desc.get('expected_outcome', 'N/A')}
Actual result: {'Success' if result.success else 'Failed'}
Details: {result.data if result.success else result.error}

Provide a brief reflection (1-2 sentences) on what this means for achieving the goal.
Respond with JSON: {{"reflection": "your analysis here"}}
"""
            system_prompt = "You are an analysis assistant for agent reflections. Be concise and actionable."
            reflection_data = await self.llm.complete_chat(system_prompt, prompt)
            
            if isinstance(reflection_data, dict):
                reflection_text = reflection_data.get("reflection", str(reflection_data))
            else:
                reflection_text = str(reflection_data)
                
        except Exception as e:
            logger.warning(f"LLM reflect failed: {e}. Using simple reflection.")
            reflection_text = f"Action {'succeeded' if result.success else 'failed'}: {result.error or result.data}"

        thought.reflection = reflection_text

        try:
            memory.store(
                f"Learned: {reflection_text}",
                {"type": "reflection", "success": result.success}
            )
        except Exception as e:
            logger.error(f"Failed to store reflection memory: {e}")

        await event_bus.emit(AgentEvent(
            time.time(), EventType.REFLECTION,
            {"thought_id": thought.step, "reflection": reflection_text}
        ))
        return thought

# -----------------------------------------------------------------------------
# ORCHESTRATOR
# -----------------------------------------------------------------------------

class MissionStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    PAUSED = auto()
    COMPLETED = auto()
    FAILED = auto()

@dataclass
class Mission:
    id: str
    goal: str
    status: MissionStatus
    created_at: float
    max_steps: int = 20
    current_step: int = 0
    context: Dict = field(default_factory=dict)

class RecoverableError(Exception):
    pass

class FatalError(Exception):
    pass

class AndroMancerAgent:
    """Agente autónomo principal con arquitectura Agent-First"""

    def __init__(self):
        self.mission: Optional[Mission] = None
        self.reasoning = ReActEngine()
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.state_file = cfg.STATE_DIR / "agent_state.json"
        self._stop_event = asyncio.Event()

        event_bus.subscribe(self._log_events)

    async def _log_events(self, event: AgentEvent):
        logger.info(f"[{event.type.name}] {event.content}")

    async def start_mission(self, goal: str, resume: bool = False) -> Mission:
        if resume and self.state_file.exists():
            self.mission = self._load_state()
            logger.info(f"Resumed mission: {self.mission.id}")
        else:
            self.mission = Mission(
                id=hashlib.md5(f"{goal}{time.time()}".encode()).hexdigest()[:8],
                goal=goal,
                status=MissionStatus.RUNNING,
                created_at=time.time(),
                max_steps=cfg.MAX_STEPS
            )
            logger.info(f"New mission started: {goal}")

        asyncio.create_task(self._run_loop())
        return self.mission

    async def _run_loop(self):
        """Main ReAct loop"""
        retry_count = 0
        max_retries = 3

        while not self._stop_event.is_set() and self.mission.status == MissionStatus.RUNNING:
            if self.mission.current_step >= self.mission.max_steps:
                logger.info("Reached max steps, completing mission")
                self.mission.status = MissionStatus.COMPLETED
                break

            try:
                # 1. OBSERVE
                ui_result = await registry.execute("get_ui", {}, {})
                if not ui_result.success:
                    raise RecoverableError(f"Observation failed: {ui_result.error}")

                observation = ui_result.data

                await event_bus.emit(AgentEvent(
                    time.time(), EventType.OBSERVATION,
                    {"step": self.mission.current_step, "screen": observation.get("summary", "")}
                ))

                # 2. REASON
                thought = await self.reasoning.reason(
                    self.mission.goal,
                    observation,
                    self.mission.current_step
                )

                if not thought.action_plan:
                    logger.info("No more actions needed, completing mission")
                    self.mission.status = MissionStatus.COMPLETED
                    break

                # 3. ACT
                results = await self._execute_plan(thought.action_plan)

                # 4. REFLECT
                for action, result in zip(thought.action_plan, results):
                    await self.reasoning.reflect(thought, result)
                    if not result.success:
                        await self._handle_failure(action, result, thought)

                retry_count = 0

                self.mission.current_step += 1
                self._save_state()

                await asyncio.sleep(0.5)

            except RecoverableError as e:
                retry_count += 1
                if retry_count > max_retries:
                    logger.error(f"Exceeded max retries: {e}")
                    self.mission.status = MissionStatus.FAILED
                    await event_bus.emit(AgentEvent(time.time(), EventType.ERROR, {"error": str(e)}))
                    break
                backoff = 2 ** retry_count
                logger.warning(f"Recoverable error (retry {retry_count}/{max_retries}): {e}. Backing off {backoff}s")
                await asyncio.sleep(backoff)
                continue

            except FatalError as e:
                logger.error(f"Fatal error: {e}")
                self.mission.status = MissionStatus.FAILED
                await event_bus.emit(AgentEvent(time.time(), EventType.ERROR, {"error": str(e)}))
                break

            except Exception as e:
                retry_count += 1
                logger.exception(f"Unhandled exception: {e}. Retry {retry_count}/{max_retries}")
                if retry_count > max_retries:
                    self.mission.status = MissionStatus.FAILED
                    await event_bus.emit(AgentEvent(time.time(), EventType.ERROR, {"error": str(e)}))
                    break
                await asyncio.sleep(2 ** retry_count)
                continue

        await self._complete_mission()

    async def _execute_plan(self, actions: List[Dict]) -> List[ExecutionResult]:
        """Ejecuta acciones"""
        if not cfg.PARALLEL_ACTIONS:
            results = []
            for action in actions:
                result = await registry.execute(
                    action["capability"],
                    action.get("params", {}),
                    {"mission": self.mission.id}
                )
                results.append(result)
                await event_bus.emit(AgentEvent(
                    time.time(), EventType.ACTION,
                    {"capability": action["capability"], "success": result.success}
                ))
                if not result.success and action.get("critical", False):
                    break
            return results

        independent = [a for a in actions if not a.get("depends_on")]
        dependent = [a for a in actions if a.get("depends_on")]

        results: List[ExecutionResult] = []
        if independent:
            tasks = [
                registry.execute(a["capability"], a.get("params", {}), {"mission": self.mission.id})
                for a in independent
            ]
            parallel_results = await asyncio.gather(*tasks, return_exceptions=False)
            results.extend(parallel_results)

        for action in dependent:
            result = await registry.execute(
                action["capability"], action.get("params", {}), {"mission": self.mission.id}
            )
            results.append(result)

        return results

    async def _handle_failure(self, action: Dict, result: ExecutionResult, thought: Thought):
        """Recuperación inteligente de errores"""
        logger.warning(f"Action failed: {action['capability']}. Error: {result.error}")

        try:
            memory.store(
                f"Failed action: {action['capability']} with error: {result.error}",
                {"type": "failure", "action": action}
            )
        except Exception as e:
            logger.error(f"Memory store failed: {e}")

    async def _complete_mission(self):
        if self.mission and self.mission.status != MissionStatus.FAILED:
            self.mission.status = MissionStatus.COMPLETED
        
        await event_bus.emit(AgentEvent(
            time.time(), EventType.COMPLETION,
            {
                "mission_id": self.mission.id if self.mission else None,
                "steps": self.mission.current_step if self.mission else 0,
                "status": self.mission.status.name if self.mission else "UNKNOWN"
            }
        ))
        self._cleanup()

    def _save_state(self):
        try:
            cfg.STATE_DIR.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, 'w') as f:
                mission_dict = asdict(self.mission)
                mission_dict['status'] = self.mission.status.name
                json.dump(mission_dict, f)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def _load_state(self) -> Mission:
        with open(self.state_file) as f:
            data = json.load(f)
            data['status'] = MissionStatus[data['status']]
            return Mission(**data)

    def _cleanup(self):
        if self.state_file.exists():
            try:
                self.state_file.rename(cfg.STATE_DIR / f"completed_{self.mission.id}.json")
            except Exception as e:
                logger.warning(f"Cleanup rename failed: {e}")

    async def pause(self):
        if self.mission:
            self.mission.status = MissionStatus.PAUSED
            self._save_state()

    def stop(self):
        self._stop_event.set()

# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

class AndroMancerCLI:
    """Interfaz de usuario"""

    def __init__(self):
        self.agent = AndroMancerAgent()
        self.commands = {
            "mission": self._cmd_mission,
            "status": self._cmd_status,
            "memory": self._cmd_memory,
            "stop": self._cmd_stop,
            "capabilities": self._cmd_capabilities,
            "help": self._cmd_help
        }

    async def run(self):
        print("🔮 AndroMancer v11.0 - Agent-First Architecture")
        print("Commands: mission <goal>, status, memory, capabilities, stop, help")
        print()

        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, input, "\n🤖 Agent> "
                )
                parts = line.strip().split(maxsplit=1)
                if not parts:
                    continue

                cmd = parts[0]
                args = parts[1] if len(parts) > 1 else ""
                
                if cmd in self.commands:
                    await self.commands[cmd](args)
                else:
                    await self._cmd_mission(line)

            except KeyboardInterrupt:
                print("\n\nInterrupted by user")
                await self._cmd_stop("")
                break
            except EOFError:
                break
            except Exception as e:
                print(f"❌ Error: {e}")

    async def _cmd_mission(self, goal: str):
        if not goal or goal.strip() == "":
            print("Usage: mission <description>")
            print("Example: mission abre whatsapp y envía mensaje a Juan")
            return
        
        try:
            mission = await self.agent.start_mission(goal)
            print(f"✅ Started mission: {mission.id}")
            print(f"📝 Goal: {goal}")
            print()
            
            asyncio.create_task(self._monitor_mission())
        except Exception as e:
            print(f"❌ Failed to start mission: {e}")

    async def _monitor_mission(self):
        last_step = -1
        while self.agent.mission and self.agent.mission.status == MissionStatus.RUNNING:
            await asyncio.sleep(1)
            if self.agent.mission.current_step != last_step:
                last_step = self.agent.mission.current_step
                print(f"📍 Step {self.agent.mission.current_step}/{self.agent.mission.max_steps}", end="\r")
        
        if self.agent.mission:
            print()
            if self.agent.mission.status == MissionStatus.COMPLETED:
                print(f"✅ Mission completed in {self.agent.mission.current_step} steps")
            elif self.agent.mission.status == MissionStatus.FAILED:
                print(f"❌ Mission failed at step {self.agent.mission.current_step}")

    async def _cmd_status(self, _):
        if self.agent.mission:
            print(f"📋 Mission: {self.agent.mission.goal}")
            print(f"🔄 Status: {self.agent.mission.status.name}")
            print(f"📍 Step: {self.agent.mission.current_step}/{self.agent.mission.max_steps}")
            print(f"🕐 Started: {datetime.fromtimestamp(self.agent.mission.created_at).strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("ℹ️  No active mission")

    async def _cmd_memory(self, query: str):
        if not query:
            print(f"💾 Total memories: {len(memory.memories)}")
            if memory.memories:
                print("\nRecent memories:")
                for m in memory.memories[-5:]:
                    print(f"  [{m.id}] {m.content[:60]}...")
            return
        
        results = memory.retrieve(query)
        print(f"🔍 Search results for '{query}':")
        for m in results:
            print(f"  [{m.id}] {m.content[:80]}... (accessed: {m.access_count}x)")

    async def _cmd_capabilities(self, _):
        caps = registry.list_capabilities()
        print("🛠️  Available capabilities:")
        for cap in caps:
            risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴", "critical": "⛔"}.get(cap['risk'], "⚪")
            print(f"  {risk_emoji} {cap['name']}: {cap['description']}")

    async def _cmd_help(self, _):
        print("""
🔮 AndroMancer v11.0 - Commands

  mission <goal>     - Start new autonomous mission
  status             - Show current mission status
  memory [query]     - View/search memory store
  capabilities       - List available actions
  stop               - Stop current mission
  help               - Show this help

Examples:
  mission abre whatsapp
  mission busca restaurantes italianos en maps
  mission envía mensaje a Juan: Hola
""")

    async def _cmd_stop(self, _):
        print("🛑 Stopping agent...")
        self.agent.stop()
        await asyncio.sleep(0.5)

# -----------------------------------------------------------------------------
# ENTRY POINT
# -----------------------------------------------------------------------------

async def main():
    try:
        import httpx
    except ImportError:
        print("⚠️  httpx not found. Installing...")
        print("Run: pip install httpx --break-system-packages")
        return
    
    try:
        result = subprocess.run(["adb", "version"], capture_output=True, timeout=5)
        if result.returncode != 0:
            print("⚠️  ADB not found. Install with: pkg install android-tools")
            return
    except Exception:
        print("⚠️  ADB not accessible. Make sure android-tools is installed")
        return
    
    cli = AndroMancerCLI()
    await cli.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
