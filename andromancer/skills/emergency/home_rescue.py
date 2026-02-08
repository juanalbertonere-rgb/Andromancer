from typing import Dict, Any, List
from andromancer.skills.base import Skill, SkillResult, SkillPriority

class EmergencyHomeSkill(Skill):
    name = "HomeRescue"
    priority = SkillPriority.EMERGENCY

    async def evaluate(self, goal: str, observation: Dict[str, Any], history: List[Any]) -> SkillResult:
        # If we have reached 5 steps, it might be a good time to reset if not finished
        if len(history) >= 5:
            # Check if any recent action was successful
            recent_success = any("Success" in (t.reflection or "") for t in history[-3:])

            if not recent_success:
                return SkillResult(
                    can_handle=True,
                    confidence=0.93,
                    actions=[{"capability": "open_app", "params": {"app_name": "HOME"}}],
                    override_llm=True,
                    suggestion="Emergency: No progress in 5 steps. Resetting to HOME."
                )

        return SkillResult(can_handle=False, confidence=0.0, actions=[])
