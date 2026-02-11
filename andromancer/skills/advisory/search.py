from typing import Dict, Any, List
from andromancer.skills.base import Skill, SkillResult, SkillPriority

class SearchSkill(Skill):
    """Skill that helps the agent identify and use search functionalities within apps."""
    name = "SearchHelper"
    priority = SkillPriority.ADVISORY

    async def evaluate(self, goal: str, observation: Dict[str, Any], history: List[Any]) -> SkillResult:
        goal_lower = goal.lower()
        # Keywords that indicate a search intent
        search_keywords = ["busca", "search", "find", "encontrar", "lupa", "quien es", "donde esta"]

        is_searching = any(k in goal_lower for k in search_keywords)
        if not is_searching:
            return SkillResult(can_handle=False, confidence=0.0, actions=[])

        elements = observation.get("elements", [])
        search_elements = []

        # Look for search-related UI elements
        for e in elements:
            text = (e.get("text") or "").lower()
            desc = (e.get("content_desc") or "").lower()
            res_id = (e.get("resource_id") or "").lower()

            indicators = ["search", "buscar", "lupa", "query", "find", "input_search", "search_src_text"]
            if any(k in text or k in desc or k in res_id for k in indicators):
                search_elements.append(e)

        if search_elements:
            # Check if we already tried to use search recently to avoid redundant suggestions
            last_actions = []
            for thought in history[-3:]:
                if thought.action_plan:
                    for action in thought.action_plan:
                        last_actions.append(action.get("capability"))

            if "type" in last_actions:
                 return SkillResult(can_handle=False, confidence=0.0, actions=[])

            return SkillResult(
                can_handle=True,
                confidence=0.8,
                actions=[], # It's an advisory skill, so it just suggests to the LLM
                override_llm=False,
                suggestion="He detectado un botón o campo de búsqueda que parece relevante para tu objetivo. Usarlo podría ser más eficiente que navegar manualmente."
            )

        return SkillResult(can_handle=False, confidence=0.0, actions=[])
