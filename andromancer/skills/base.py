from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum, auto

class SkillPriority(Enum):
    CRITICAL = auto() # Overrides LLM if confidence > threshold
    ADVISORY = auto() # Suggestion to LLM
    EMERGENCY = auto() # Rescue skill

@dataclass
class SkillResult:
    actions: List[Dict[str, Any]]
    confidence: float
    can_handle: bool
    override_llm: bool = False
    execute_atomic: bool = True
    suggestion: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class Skill(ABC):
    name: str
    priority: SkillPriority

    @abstractmethod
    async def evaluate(self, goal: str, observation: Dict[str, Any], history: List[Any]) -> SkillResult:
        """Evaluate if the skill can handle the current situation"""
        pass

class SkillRegistry:
    def __init__(self):
        self._skills: List[Skill] = []

    def register(self, skill: Skill):
        self._skills.append(skill)

    async def check_skills(self, goal: str, observation: Dict[str, Any], history: List[Any]) -> Tuple[Optional[SkillResult], List[str]]:
        suggestions = []
        best_override = None

        for skill in self._skills:
            try:
                result = await skill.evaluate(goal, observation, history)
                if result.can_handle:
                    if result.override_llm and (not best_override or result.confidence > best_override.confidence):
                        if result.confidence > 0.9: # Threshold for override
                            best_override = result

                    if result.suggestion:
                        suggestions.append(f"{skill.name}: {result.suggestion}")
            except Exception as e:
                import logging
                logging.getLogger("AndroMancer.Skills").error(f"Error evaluating skill {skill.name}: {e}")

        return best_override, suggestions
