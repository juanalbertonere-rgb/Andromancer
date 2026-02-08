from typing import Dict, Any, List
from andromancer.skills.base import Skill, SkillResult, SkillPriority

class SettingsEscapeSkill(Skill):
    name = "SettingsEscape"
    priority = SkillPriority.ADVISORY

    async def evaluate(self, goal: str, observation: Dict[str, Any], history: List[Any]) -> SkillResult:
        summary = observation.get("summary", "").lower()
        goal_lower = goal.lower()

        # If we are in settings but the goal doesn't seem to involve settings
        if "settings" in summary or "ajustes" in summary or "configuraci" in summary:
            if "settings" not in goal_lower and "ajustes" not in goal_lower and "wifi" not in goal_lower:
                return SkillResult(
                    can_handle=True,
                    confidence=0.7,
                    actions=[], # No actions, just suggestion
                    override_llm=False,
                    suggestion="We seem to be in Settings, but the goal doesn't mention it. Consider going BACK or HOME."
                )

        return SkillResult(can_handle=False, confidence=0.0, actions=[])
