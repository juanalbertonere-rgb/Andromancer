from typing import Dict, Any, List
from andromancer.skills.base import Skill, SkillResult, SkillPriority

class ExplorationSkill(Skill):
    """Skill that encourages exploring unknown or complex UIs."""
    name = "ExplorationHelper"
    priority = SkillPriority.ADVISORY

    async def evaluate(self, goal: str, observation: Dict[str, Any], history: List[Any]) -> SkillResult:
        package = observation.get("current_package", "").lower()

        # If we have many elements but no clear idea what to do
        elements = observation.get("elements", [])

        # Check if we have been in this package for multiple steps without success
        steps_in_current_package = 0
        for thought in history[-5:]:
            if thought.observation and thought.observation.get("current_package", "").lower() == package:
                steps_in_current_package += 1

        if steps_in_current_package >= 3:
            return SkillResult(
                can_handle=True,
                confidence=0.75,
                actions=[],
                override_llm=False,
                suggestion=(
                    f"Has estado en {package} durante varios pasos. "
                    "Si te sientes bloqueado, intenta buscar botones de 'menú', 'buscar', 'atrás' o 'inicio'. "
                    "También puedes intentar un 'swipe' para ver si hay más contenido oculto."
                )
            )

        return SkillResult(can_handle=False, confidence=0.0, actions=[])
