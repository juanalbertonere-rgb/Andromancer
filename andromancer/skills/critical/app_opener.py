import re
from typing import Dict, Any, List
from andromancer.skills.base import Skill, SkillResult, SkillPriority
from andromancer.utils.adb import adb_manager
from andromancer.utils.apps import get_package_name
from andromancer.utils.text import normalize_text

class AppOpenerSkill(Skill):
    name = "AppOpener"
    priority = SkillPriority.CRITICAL

    async def evaluate(self, goal: str, observation: Dict[str, Any], history: List[Any]) -> SkillResult:
        goal_norm = normalize_text(goal)

        # 1. Detect intent and app name candidate
        # Matches "abre whatsapp", "open settings", "abre el chat de whatsapp", etc.
        # Supports both Spanish and English triggers and filler words
        triggers = r"abre|open|lanza|launch|ve a|go to|pon|start|busca|search"
        fillers = r"la aplicacion de|the app|el app|la app|app|el chat de|the chat|de|el|la|un|una|the"

        pattern = rf"(?:{triggers})\s+(?:(?:{fillers})\s+)*([a-z0-9\s]+)"
        match = re.search(pattern, goal_norm)

        if not match:
            return SkillResult(can_handle=False, confidence=0.0, actions=[])

        captured = match.group(1).strip()

        # Handle multi-word apps like "play store"
        if captured.startswith("play store"):
            app_name = "play store"
        else:
            app_name = captured.split()[0]

        # Noise filter
        if not app_name or app_name in ["este", "ese", "aqui", "here", "la", "el"]:
            return SkillResult(can_handle=False, confidence=0.0, actions=[])

        # Level 1: Centralized Map
        target_package = get_package_name(app_name)
        current_package = observation.get("current_package", "")

        # 2. Check if already open
        if target_package and current_package == target_package:
            return SkillResult(
                can_handle=True,
                confidence=0.1, # Very low confidence, we are already there
                actions=[],
                override_llm=False,
                suggestion=f"App {app_name} is already in foreground."
            )

        # 3. Check history to avoid loops
        last_attempts = []
        for thought in history[-3:]:
            if thought.action_plan:
                for action in thought.action_plan:
                    if action.get("capability") == "open_app":
                        last_attempts.append(action.get("params", {}).get("app_name"))

        if app_name in last_attempts or (target_package and target_package in last_attempts):
            return SkillResult(
                can_handle=True,
                confidence=0.5, # Let LLM decide since previous open_app didn't seem to satisfy the goal
                actions=[],
                override_llm=False,
                suggestion=f"Recently tried opening {app_name}, letting LLM reason next steps."
            )

        # 4. Decision logic
        if target_package:
            return SkillResult(
                can_handle=True,
                confidence=0.95,
                actions=[{"capability": "open_app", "params": {"app_name": app_name}}],
                override_llm=True,
                suggestion=f"Opening known app: {app_name}"
            )

        # Level 2: ADB Package search (if not a common word)
        if len(app_name) > 2:
            try:
                await adb_manager.ensure_connected()
                result = await adb_manager._run(["adb", "shell", "pm", "list", "packages"])
                if result.returncode == 0:
                    packages = result.stdout.splitlines()
                    for p in packages:
                        p_name = p.replace("package:", "").strip()
                        if app_name == p_name.split('.')[-1].lower() or app_name == p_name.lower():
                            return SkillResult(
                                can_handle=True,
                                confidence=0.91,
                                actions=[{"capability": "open_app", "params": {"app_name": p_name}}],
                                override_llm=True,
                                suggestion=f"Found package via ADB: {p_name}"
                            )
            except Exception:
                pass

        return SkillResult(can_handle=False, confidence=0.0, actions=[])
