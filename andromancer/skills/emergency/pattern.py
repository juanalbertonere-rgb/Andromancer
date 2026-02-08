from typing import Dict, Any, List
from andromancer.skills.base import Skill, SkillResult, SkillPriority

class PatternSkill(Skill):
    name = "PatternDetector"
    priority = SkillPriority.EMERGENCY

    async def evaluate(self, goal: str, observation: Dict[str, Any], history: List[Any]) -> SkillResult:
        if len(history) < 3:
            return SkillResult(can_handle=False, confidence=0.0, actions=[])

        # 1. Same action 3+ times
        last_actions = []
        for thought in history[-3:]:
            if thought.action_plan:
                last_actions.append(thought.action_plan[0].get("capability"))

        if len(last_actions) == 3 and len(set(last_actions)) == 1:
            return SkillResult(
                can_handle=True,
                confidence=0.91,
                actions=[{"capability": "back", "params": {}}],
                override_llm=True,
                suggestion="Detected repeated actions. Trying to go BACK to break the loop."
            )

        # 2. Same screen summary 3+ times (Stagnation)
        last_summaries = []
        for thought in history[-3:]:
            if thought.observation and "summary" in thought.observation:
                last_summaries.append(thought.observation["summary"])

        if len(last_summaries) == 3 and len(set(last_summaries)) == 1:
            return SkillResult(
                can_handle=True,
                confidence=0.92,
                actions=[{"capability": "open_app", "params": {"app_name": "HOME"}}],
                override_llm=True,
                suggestion="UI seems stuck. Going HOME to reset context."
            )

        return SkillResult(can_handle=False, confidence=0.0, actions=[])
