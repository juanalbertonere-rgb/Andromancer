import asyncio
import time
import hashlib
import logging
import json
from enum import Enum, auto
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Callable, Coroutine
from collections import deque
from concurrent.futures import ThreadPoolExecutor

from andromancer import config as cfg
from andromancer.core.capabilities.base import CapabilityRegistry, ExecutionResult
from andromancer.core.reasoning import ReActEngine, Thought
from andromancer.core.memory import memory_store
from andromancer.skills.base import SkillRegistry, SkillResult
from andromancer.skills.critical.app_opener import AppOpenerSkill
from andromancer.skills.advisory.settings_escape import SettingsEscapeSkill
from andromancer.skills.advisory.search import SearchSkill
from andromancer.skills.advisory.scroll import ScrollSkill
from andromancer.skills.advisory.exploration import ExplorationSkill
from andromancer.skills.emergency.pattern import PatternSkill
from andromancer.skills.emergency.home_rescue import EmergencyHomeSkill

from andromancer.core.capabilities.interaction import TapCapability, TypeCapability, SwipeCapability, BackCapability
from andromancer.core.capabilities.observation import UIScrapeCapability
from andromancer.core.capabilities.navigation import OpenAppCapability, WaitCapability
from andromancer.core.capabilities.secrets import GetSecretCapability

logger = logging.getLogger("AndroMancer.Agent")

class EventType(Enum):
    THOUGHT = auto()
    ACTION = auto()
    OBSERVATION = auto()
    REFLECTION = auto()
    ERROR = auto()
    COMPLETION = auto()
    SAFETY_CHECK = auto()
    SKILL_START = auto()
    SKILL_END = auto()
    REPORT = auto()

@dataclass
class AgentEvent:
    timestamp: float
    type: EventType
    content: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

class EventBus:
    """Decoupled event system"""
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
    """Main autonomous agent"""

    def __init__(self):
        self.mission: Optional[Mission] = None
        self.reasoning = ReActEngine()
        self.registry = CapabilityRegistry()
        self.registry.safety_check_callback = self._check_safety
        self._register_default_capabilities()
        self.skill_registry = SkillRegistry()
        self._register_default_skills()
        self.state_file = cfg.STATE_FILE
        self._stop_event = asyncio.Event()

        event_bus.subscribe(self._log_events)

    def _register_default_capabilities(self):
        self.registry.register(TapCapability())
        self.registry.register(TypeCapability())
        self.registry.register(SwipeCapability())
        self.registry.register(BackCapability())
        self.registry.register(UIScrapeCapability())
        self.registry.register(OpenAppCapability())
        self.registry.register(GetSecretCapability())
        self.registry.register(WaitCapability())

    def _register_default_skills(self):
        self.skill_registry.register(AppOpenerSkill())
        self.skill_registry.register(SettingsEscapeSkill())
        self.skill_registry.register(SearchSkill())
        self.skill_registry.register(ScrollSkill())
        self.skill_registry.register(ExplorationSkill())
        self.skill_registry.register(PatternSkill())
        self.skill_registry.register(EmergencyHomeSkill())

    async def _log_events(self, event: AgentEvent):
        """Logs events and handles silent mode logic if necessary."""
        logger.info(f"[{event.type.name}] {event.content}")
        # In silent mode, CLI suppresses step indicators, but core events still reach subscribers.

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
        retry_count = 0
        max_retries = 3

        while not self._stop_event.is_set() and self.mission.status == MissionStatus.RUNNING:
            if self.mission.current_step >= self.mission.max_steps:
                logger.info("Reached max steps, completing mission")
                self.mission.status = MissionStatus.COMPLETED
                break

            try:
                # 1. OBSERVE
                ui_result = await self.registry.execute("get_ui", {})
                if not ui_result.success:
                    raise RecoverableError(f"Observation failed: {ui_result.error}")

                observation = ui_result.data
                memory_store.store(observation.get("summary", ""), {"type": "screen", "mission": self.mission.id})

                await event_bus.emit(AgentEvent(
                    time.time(), EventType.OBSERVATION,
                    {"step": self.mission.current_step, "screen": observation.get("summary", "")}
                ))

                # --- SKILL CHECK ---
                skill_override, skill_suggestions = await self.skill_registry.check_skills(
                    self.mission.goal,
                    observation,
                    self.reasoning.thought_history
                )

                if skill_override:
                    await event_bus.emit(AgentEvent(
                        time.time(), EventType.SKILL_START,
                        {"skill_override": True, "actions": len(skill_override.actions)}
                    ))

                    # Execute skill plan
                    results = await self._execute_plan(skill_override.actions)

                    await event_bus.emit(AgentEvent(
                        time.time(), EventType.SKILL_END,
                        {"success": all(r.success for r in results)}
                    ))

                    # Reflection on skill execution
                    dummy_thought = Thought(
                        step=self.mission.current_step,
                        reasoning=f"Skill override executed: {skill_override.suggestion}",
                        action_plan=skill_override.actions,
                        confidence=skill_override.confidence,
                        observation=observation
                    )
                    for action, result in zip(skill_override.actions, results):
                        await self.reasoning.reflect(dummy_thought, result)

                    self.reasoning.thought_history.append(dummy_thought)

                else:
                    # 2. REASON
                    thought = await self.reasoning.reason(
                        self.mission.goal,
                        observation,
                        self.mission.current_step,
                        self.registry.list_capabilities(),
                        skill_suggestions=skill_suggestions
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
                        else:
                            # Clear previous errors if we have a success
                            self.reasoning.working_memory.pop("last_action_error", None)

                retry_count = 0
                self.mission.current_step += 1
                self._save_state()
                await asyncio.sleep(0.5)

            except RecoverableError as e:
                retry_count += 1
                if retry_count > max_retries:
                    self.mission.status = MissionStatus.FAILED
                    break
                await asyncio.sleep(2 ** retry_count)
                continue
            except Exception as e:
                logger.exception(f"Unhandled exception: {e}")
                self.mission.status = MissionStatus.FAILED
                break

        await self._complete_mission()

    def _validate_action(self, action: Dict) -> Optional[str]:
        """Validates action parameters before execution"""
        cap_name = action.get("capability")
        params = action.get("params", {})

        if cap_name == "tap":
            if not (params.get("x") is not None and params.get("y") is not None) and not params.get("element"):
                return "Action 'tap' requires either 'x' and 'y' coordinates OR an 'element' dictionary. None provided. Check the UI observation again for coordinates."

        if cap_name == "type":
            if not params.get("text"):
                return "Action 'type' requires 'text' parameter."

        return None

    async def _execute_plan(self, actions: List[Dict]) -> List[ExecutionResult]:
        """Execute actions, supporting parallel execution if configured"""
        if not cfg.PARALLEL_ACTIONS:
            results = []
            for action in actions:
                error = self._validate_action(action)
                if error:
                    result = ExecutionResult(False, error=error)
                else:
                    result = await self.registry.execute(
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

        # Parallel logic
        independent = [a for a in actions if not a.get("depends_on")]
        dependent = [a for a in actions if a.get("depends_on")]

        results: List[ExecutionResult] = []
        if independent:
            tasks = []
            for a in independent:
                error = self._validate_action(a)
                if error:
                    # Create a dummy task that returns the error
                    async def dummy_fail(e): return ExecutionResult(False, error=e)
                    tasks.append(dummy_fail(error))
                else:
                    tasks.append(self.registry.execute(a["capability"], a.get("params", {}), {"mission": self.mission.id}))

            parallel_results = await asyncio.gather(*tasks, return_exceptions=False)
            results.extend(parallel_results)

            for action, result in zip(independent, parallel_results):
                await event_bus.emit(AgentEvent(
                    time.time(), EventType.ACTION,
                    {"capability": action["capability"], "success": result.success}
                ))

        for action in dependent:
            error = self._validate_action(action)
            if error:
                result = ExecutionResult(False, error=error)
            else:
                result = await self.registry.execute(
                    action["capability"], action.get("params", {}), {"mission": self.mission.id}
                )
            results.append(result)
            await event_bus.emit(AgentEvent(
                time.time(), EventType.ACTION,
                {"capability": action["capability"], "success": result.success}
            ))

        return results

    async def _check_safety(self, name: str, params: Dict, context: Dict) -> bool:
        await event_bus.emit(AgentEvent(
            time.time(), EventType.SAFETY_CHECK,
            {"capability": name, "params": params}
        ))
        # Automatic approval for now, as in original code
        return True

    async def _handle_failure(self, action: Dict, result: ExecutionResult, thought: Thought):
        logger.warning(f"Action failed: {action['capability']}. Error: {result.error}")
        self.reasoning.working_memory["last_action_error"] = f"Action '{action['capability']}' failed: {result.error}"

    async def _complete_mission(self):
        if self.mission and self.mission.status != MissionStatus.FAILED:
            self.mission.status = MissionStatus.COMPLETED

        # Generate AI Summary
        summary = "Misión finalizada."
        if self.mission:
            summary = await self.reasoning.generate_summary(
                self.mission.goal,
                self.mission.status.name
            )
            print(f"\n🤖 {summary}\n") # Output to console for user

        await event_bus.emit(AgentEvent(
            time.time(), EventType.REPORT,
            {"summary": summary}
        ))

        await event_bus.emit(AgentEvent(
            time.time(), EventType.COMPLETION,
            {"mission_id": self.mission.id if self.mission else None, "status": self.mission.status.name if self.mission else "UNKNOWN"}
        ))

    def _save_state(self):
        try:
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

    def stop(self):
        self._stop_event.set()
