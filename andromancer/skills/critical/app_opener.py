import re
from typing import Dict, Any, List
from andromancer.skills.base import Skill, SkillResult, SkillPriority
from andromancer.utils.adb import adb_manager

class AppOpenerSkill(Skill):
    name = "AppOpener"
    priority = SkillPriority.CRITICAL

    async def evaluate(self, goal: str, observation: Dict[str, Any], history: List[Any]) -> SkillResult:
        goal_lower = goal.lower()
        # Regex to find "abre <app>" or "open <app>"
        match = re.search(r"(?:abre|open|lanza)\s+([a-zA-Z0-9]+)", goal_lower)

        if match:
            app_name = match.group(1)

            # Level 1: Simple Map
            app_map = {
                "whatsapp": "com.whatsapp",
                "chrome": "com.android.chrome",
                "settings": "com.android.settings",
                "instagram": "com.instagram.android",
                "twitter": "com.twitter.android",
                "gmail": "com.google.android.gm"
            }

            if app_name in app_map:
                return SkillResult(
                    can_handle=True,
                    confidence=0.95,
                    actions=[{"capability": "open_app", "params": {"app_name": app_name}}],
                    override_llm=True,
                    suggestion=f"Opening known app: {app_name}"
                )

            # Level 2: ADB Package search
            try:
                await adb_manager.ensure_connected()
                result = await adb_manager._run(["adb", "shell", "pm", "list", "packages"])
                if result.returncode == 0:
                    packages = result.stdout.splitlines()
                    for p in packages:
                        if app_name in p.lower():
                            package_name = p.replace("package:", "").strip()
                            return SkillResult(
                                can_handle=True,
                                confidence=0.91,
                                actions=[{"capability": "open_app", "params": {"app_name": package_name}}],
                                override_llm=True,
                                suggestion=f"Found package via ADB: {package_name}"
                            )
            except Exception:
                pass

        return SkillResult(can_handle=False, confidence=0.0, actions=[])
