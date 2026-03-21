"""Pydantic models for Mental Mastery data structures."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class SkillCategory(str, Enum):
    """Categories of mental skills."""
    COMPUTATIONAL = "computational"  # Арифметические операции
    MEMORY = "memory"  # Работа с памятью (working memory)
    VISUALIZATION = "visualization"  # Мысленная визуализация
    STRATEGIC = "strategic"  # Выбор стратегии решения
    MNEMONIC = "mnemonic"  # Мнемотехники
    CONCEPTUAL = "conceptual"  # Понимание концепций


class Difficulty(str, Enum):
    """Exercise difficulty levels."""
    INTRO = "intro"  # Знакомство с навыком
    BASIC = "basic"  # Базовое применение
    INTERMEDIATE = "intermediate"  # Комбинация навыков
    ADVANCED = "advanced"  # Сложный контекст
    MASTERY = "mastery"  # Уровень оригинальной задачи


class Skill(BaseModel):
    """Represents a single mental skill."""
    id: str = Field(..., description="Unique skill identifier")
    name: str = Field(..., description="Human-readable skill name")
    description: str = Field(..., description="Detailed skill description")
    category: SkillCategory
    difficulty_base: int = Field(..., ge=1, le=10, description="Base difficulty 1-10")
    cognitive_load: int = Field(..., ge=1, le=10, description="Working memory load 1-10")
    prerequisites: list[str] = Field(default_factory=list, description="Required skill IDs")
    tips: list[str] = Field(default_factory=list, description="Tips for mastering this skill")
    mnemonics: Optional[str] = Field(None, description="Mnemonic technique for this skill")


class Exercise(BaseModel):
    """A single exercise for practicing a skill."""
    id: str = Field(..., description="Unique exercise ID")
    skill_id: str = Field(..., description="Parent skill ID")
    level: Difficulty
    question: str = Field(..., description="Exercise question in LaTeX")
    question_plain: str = Field(..., description="Plain text version")
    answer: str = Field(..., description="Correct answer")
    solution_steps: list[str] = Field(..., description="Step-by-step solution")
    hints: list[str] = Field(default_factory=list, description="Progressive hints")
    time_estimate: int = Field(..., description="Estimated time in seconds")
    cognitive_load: int = Field(..., ge=1, le=10)


class TaskDecomposition(BaseModel):
    """Result of decomposing a complex task into skills."""
    original_task: str = Field(..., description="Original task LaTeX")
    original_task_plain: str = Field(..., description="Plain text version")
    full_solution: list[str] = Field(..., description="Complete step-by-step solution")
    skills: list[Skill] = Field(..., description="Identified skills")
    skill_graph: dict[str, list[str]] = Field(..., description="Skill dependencies DAG")
    exercises: dict[str, list[Exercise]] = Field(..., description="Exercises per skill")
    estimated_total_time: int = Field(..., description="Total training time in minutes")
    created_at: datetime = Field(default_factory=datetime.now)


class UserProgress(BaseModel):
    """User's progress on a skill."""
    skill_id: str
    level: Difficulty = Difficulty.INTRO
    exercises_completed: int = 0
    exercises_correct: int = 0
    streak: int = 0
    last_practiced: Optional[datetime] = None
    mastery_score: float = 0.0  # 0.0 to 1.0


class TaskProgress(BaseModel):
    """User's progress on a decomposed task."""
    task_id: str
    decomposition: TaskDecomposition
    skill_progress: dict[str, UserProgress] = Field(default_factory=dict)
    started_at: datetime = Field(default_factory=datetime.now)
    completed: bool = False
    can_solve_original: bool = False  # Ready to solve original task

    def get_next_skill(self) -> Optional[str]:
        """Get next skill to practice based on dependencies and progress."""
        for skill_id in self.decomposition.skill_graph.get("order", []):
            if skill_id not in self.skill_progress:
                # Check prerequisites
                prereqs = self.decomposition.skill_graph.get(skill_id, [])
                if all(
                    self.skill_progress.get(p, UserProgress(skill_id=p)).mastery_score >= 0.8
                    for p in prereqs
                ):
                    return skill_id
            elif self.skill_progress[skill_id].mastery_score < 0.8:
                return skill_id
        return None


class Session(BaseModel):
    """Training session data."""
    session_id: str
    tasks: dict[str, TaskProgress] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    total_exercises: int = 0
    total_correct: int = 0
