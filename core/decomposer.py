"""Task decomposition module."""

import json
import uuid
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from llm import LLMClient
from models import (
    TaskDecomposition,
    Skill,
    Exercise,
    Difficulty,
    SkillCategory,
)

console = Console()


class TaskDecomposer:
    """Decomposes tasks into skills and exercises."""

    def __init__(
        self,
        llm_client: LLMClient,
        cache_dir: Optional[Path] = None,
        use_cache: bool = True
    ):
        self.llm = llm_client
        self.cache_dir = cache_dir or Path.home() / ".mental_mastery" / "cache"
        self.use_cache = use_cache
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, task: str) -> Path:
        """Get cache file path for a task."""
        import hashlib
        task_hash = hashlib.md5(task.encode()).hexdigest()
        return self.cache_dir / f"decomposition_{task_hash}.json"

    def _load_cache(self, task: str) -> Optional[TaskDecomposition]:
        """Load cached decomposition if exists."""
        if not self.use_cache:
            return None

        cache_path = self._get_cache_path(task)
        if cache_path.exists():
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return TaskDecomposition(**data)
            except Exception as e:
                console.print(f"[yellow]Cache load error: {e}[/yellow]")
        return None

    def _save_cache(self, task: str, decomposition: TaskDecomposition):
        """Save decomposition to cache."""
        cache_path = self._get_cache_path(task)
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(decomposition.model_dump(), f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            console.print(f"[yellow]Cache save error: {e}[/yellow]")

    def decompose(
        self,
        task: str,
        task_type: str = "math",
        generate_exercises: bool = True
    ) -> TaskDecomposition:
        """Decompose a task into skills and optionally generate exercises."""

        # Check cache first
        cached = self._load_cache(task)
        if cached:
            console.print("[green]✓ Loaded from cache[/green]")
            return cached

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:

            # Step 1: Decompose task
            task_id = progress.add_task("Decomposing task into skills...", total=None)
            decomposition_data = self.llm.decompose_task(task, task_type)
            progress.remove_task(task_id)

            # Parse skills
            skills = []
            for skill_data in decomposition_data.get("skills", []):
                try:
                    skill = Skill(
                        id=skill_data["id"],
                        name=skill_data["name"],
                        description=skill_data["description"],
                        category=SkillCategory(skill_data.get("category", "computational").lower()),
                        difficulty_base=skill_data.get("difficulty_base", 5),
                        cognitive_load=skill_data.get("cognitive_load", 5),
                        prerequisites=skill_data.get("prerequisites", []),
                        tips=skill_data.get("tips", []),
                        mnemonics=skill_data.get("mnemonics"),
                    )
                    skills.append(skill)
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not parse skill: {e}[/yellow]")

            # Step 2: Generate exercises for each skill
            exercises = {}
            if generate_exercises:
                for skill in skills:
                    task_id = progress.add_task(
                        f"Generating exercises for: {skill.name}...",
                        total=None
                    )
                    try:
                        ex_data = self.llm.generate_exercises(
                            skill.model_dump(),
                            str(decomposition_data.get("full_solution", [])),
                            skill.id
                        )
                        skill_exercises = []
                        for ex in ex_data.get("exercises", []):
                            try:
                                exercise = Exercise(
                                    id=ex.get("id", str(uuid.uuid4())),
                                    skill_id=skill.id,
                                    level=Difficulty(ex.get("level", "intro")),
                                    question=ex["question"],
                                    question_plain=ex["question_plain"],
                                    answer=ex["answer"],
                                    solution_steps=ex.get("solution_steps", []),
                                    hints=ex.get("hints", []),
                                    time_estimate=ex.get("time_estimate", 30),
                                    cognitive_load=ex.get("cognitive_load", 5),
                                )
                                skill_exercises.append(exercise)
                            except Exception as e:
                                console.print(f"[yellow]Warning: Could not parse exercise: {e}[/yellow]")
                        exercises[skill.id] = skill_exercises
                    except Exception as e:
                        console.print(f"[red]Error generating exercises for {skill.id}: {e}[/red]")
                        exercises[skill.id] = []
                    progress.remove_task(task_id)

            # Create decomposition object
            decomposition = TaskDecomposition(
                original_task=decomposition_data.get("original_task", task),
                original_task_plain=decomposition_data.get("original_task_plain", task),
                full_solution=decomposition_data.get("full_solution", []),
                skills=skills,
                skill_graph=decomposition_data.get("skill_graph", {}),
                exercises=exercises,
                estimated_total_time=sum(
                    sum(ex.time_estimate for ex in exs)
                    for exs in exercises.values()
                ) // 60,  # Convert to minutes
            )

            # Save to cache
            self._save_cache(task, decomposition)

            return decomposition

    def verify_exercise(self, exercise: Exercise, user_answer: str) -> dict:
        """Verify user's answer to an exercise."""
        return self.llm.verify_answer(exercise.model_dump(), user_answer)
