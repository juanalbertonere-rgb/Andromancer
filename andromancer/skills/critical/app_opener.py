import re
from typing import Dict, Any, List
from andromancer.skills.base import Skill, SkillResult, SkillPriority
from andromancer.utils.adb import adb_manager

class AppOpenerSkill(Skill):
    name = "AppOpener"
    priority = SkillPriority.CRITICAL

    async def evaluate(self, goal: str, observation: Dict[str, Any], history: List[Any]) -> SkillResult:
        goal_lower = goal.lower()

        # 1. Detect intent and app name candidate
        # Matches "abre whatsapp", "open settings", "abre el chat de whatsapp", etc.
        # Note: Ordered from most specific to least specific
        match = re.search(r"(?:abre|open|lanza|ve a)\s+(?:el\s+chat\s+de\s+|la\s+app\s+de\s+|el\s+|la\s+)?([a-zA-Z0-9]+)", goal_lower)

        if not match:
            return SkillResult(can_handle=False, confidence=0.0, actions=[])

        app_name = match.group(1).lower()

        # Noise filter
        if app_name in ["el", "la", "un", "una", "chat", "app", "este", "ese"]:
            return SkillResult(can_handle=False, confidence=0.0, actions=[])

        # Level 1: Simple Map
        app_map = {
            "whatsapp": "com.whatsapp",
            "chrome": "com.android.chrome",
            "settings": "com.android.settings",
            "ajustes": "com.android.settings",
            "configuracion": "com.android.settings",
            "instagram": "com.instagram.android",
            "twitter": "com.twitter.android",
            "gmail": "com.google.android.gm",
            "youtube": "com.google.android.youtube",
            "facebook": "com.facebook.katana"
        }

        target_package = app_map.get(app_name)
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
