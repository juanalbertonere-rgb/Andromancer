from typing import Dict, Any, List
from andromancer.skills.base import Skill, SkillResult, SkillPriority

class ScrollSkill(Skill):
    """Skill that suggests scrolling when the target element might be off-screen."""
    name = "ScrollHelper"
    priority = SkillPriority.ADVISORY

    async def evaluate(self, goal: str, observation: Dict[str, Any], history: List[Any]) -> SkillResult:
        package = observation.get("current_package", "").lower()

        # Common apps where scrolling is often necessary
        list_heavy_apps = [
            "com.whatsapp",
            "com.android.settings",
            "com.google.android.contacts",
            "com.android.contacts",
            "com.android.chrome",
            "com.instagram.android",
            "com.facebook.katana"
        ]

        # Check reasoning from the last step if available
        last_thought_not_found = False
        if history:
            last_reasoning = (history[-1].reasoning or "").lower()
            not_found_indicators = ["no veo", "no encuentro", "no está", "not found", "cannot see", "missing"]
            last_thought_not_found = any(k in last_reasoning for k in not_found_indicators)

        if package in list_heavy_apps or last_thought_not_found:
            # Check how many times we have swiped recently to avoid infinite scrolling suggestions
            swipe_count = 0
            for thought in history[-5:]:
                if thought.action_plan:
                    for action in thought.action_plan:
                        if action.get("capability") == "swipe":
                            swipe_count += 1

            if swipe_count < 3:
                return SkillResult(
                    can_handle=True,
                    confidence=0.7,
                    actions=[],
                    override_llm=False,
                    suggestion="Parece que estás en una aplicación con listas o mucho contenido. Si no encuentras lo que buscas, considera usar la capacidad 'swipe' para desplazarte hacia abajo."
                )

        return SkillResult(can_handle=False, confidence=0.0, actions=[])
