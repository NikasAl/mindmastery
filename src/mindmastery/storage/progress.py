"""Storage module for user progress."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from rich.console import Console

from ..models import Session, TaskProgress, UserProgress, TaskDecomposition, Exercise

console = Console()


class ProgressStorage:
    """Manages user progress persistence."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path.home() / ".mental_mastery" / "data"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.session_file = self.storage_dir / "session.json"
        self.current_session: Optional[Session] = None

    def load_session(self) -> Session:
        """Load or create current session."""
        if self.current_session:
            return self.current_session

        if self.session_file.exists():
            try:
                with open(self.session_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.current_session = Session(**data)
                return self.current_session
            except Exception as e:
                console.print(f"[yellow]Could not load session: {e}[/yellow]")

        # Create new session
        import uuid
        self.current_session = Session(session_id=str(uuid.uuid4()))
        return self.current_session

    def save_session(self):
        """Save current session to disk."""
        if not self.current_session:
            return

        try:
            with open(self.session_file, "w", encoding="utf-8") as f:
                json.dump(
                    self.current_session.model_dump(),
                    f,
                    ensure_ascii=False,
                    indent=2,
                    default=str
                )
        except Exception as e:
            console.print(f"[red]Could not save session: {e}[/red]")

    def add_task(self, decomposition: TaskDecomposition) -> TaskProgress:
        """Add a new task to the session."""
        session = self.load_session()

        import uuid
        task_id = str(uuid.uuid4())[:8]

        task_progress = TaskProgress(
            task_id=task_id,
            decomposition=decomposition,
        )

        # Initialize skill progress
        for skill in decomposition.skills:
            task_progress.skill_progress[skill.id] = UserProgress(skill_id=skill.id)

        session.tasks[task_id] = task_progress
        self.save_session()

        return task_progress

    def has_exercises_for_skill(self, task_id: str, skill_id: str) -> bool:
        """Check if exercises exist for a skill."""
        session = self.load_session()
        
        if task_id not in session.tasks:
            return False
        
        task = session.tasks[task_id]
        exercises = task.decomposition.exercises.get(skill_id, [])
        return len(exercises) > 0

    def store_exercises_for_skill(
        self, 
        task_id: str, 
        skill_id: str, 
        exercises: List[Exercise]
    ):
        """Store generated exercises for a skill."""
        session = self.load_session()
        
        if task_id not in session.tasks:
            console.print(f"[red]Task {task_id} not found[/red]")
            return
        
        task = session.tasks[task_id]
        task.decomposition.exercises[skill_id] = exercises
        
        # Recalculate estimated time
        total_time = sum(
            sum(ex.time_estimate for ex in exs)
            for exs in task.decomposition.exercises.values()
        ) // 60
        task.decomposition.estimated_total_time = total_time if total_time > 0 else 15
        
        self.save_session()
        console.print(f"[green]✓ Exercises cached for skill {skill_id}[/green]")

    def get_exercises_for_skill(
        self, 
        task_id: str, 
        skill_id: str
    ) -> List[Exercise]:
        """Get exercises for a skill (may be empty if not generated yet)."""
        session = self.load_session()
        
        if task_id not in session.tasks:
            return []
        
        task = session.tasks[task_id]
        return task.decomposition.exercises.get(skill_id, [])

    def update_progress(
        self,
        task_id: str,
        skill_id: str,
        correct: bool,
        exercise_time: float
    ):
        """Update progress after completing an exercise."""
        session = self.load_session()

        if task_id not in session.tasks:
            console.print(f"[red]Task {task_id} not found[/red]")
            return

        task = session.tasks[task_id]
        if skill_id not in task.skill_progress:
            task.skill_progress[skill_id] = UserProgress(skill_id=skill_id)

        progress = task.skill_progress[skill_id]
        progress.exercises_completed += 1
        progress.last_practiced = datetime.now()

        if correct:
            progress.exercises_correct += 1
            progress.streak += 1
        else:
            progress.streak = 0

        # Update mastery score (moving average)
        progress.mastery_score = progress.exercises_correct / progress.exercises_completed

        # Check if can solve original task
        if all(p.mastery_score >= 0.8 for p in task.skill_progress.values()):
            task.can_solve_original = True

        session.total_exercises += 1
        if correct:
            session.total_correct += 1

        self.save_session()

    def get_stats(self) -> dict:
        """Get session statistics."""
        session = self.load_session()

        return {
            "total_tasks": len(session.tasks),
            "total_exercises": session.total_exercises,
            "accuracy": (
                session.total_correct / session.total_exercises * 100
                if session.total_exercises > 0 else 0
            ),
            "completed_tasks": sum(
                1 for t in session.tasks.values() if t.can_solve_original
            ),
        }

    def update_exercise(
        self,
        task_id: str,
        exercise_id: str,
        corrected_answer: str,
        corrected_steps: List[str]
    ) -> bool:
        """Update an exercise with corrected answer and solution steps."""
        session = self.load_session()
        
        if task_id not in session.tasks:
            console.print(f"[red]Task {task_id} not found[/red]")
            return False
        
        task = session.tasks[task_id]
        
        # Find and update the exercise
        for skill_id, exercises in task.decomposition.exercises.items():
            for i, ex in enumerate(exercises):
                if ex.id == exercise_id:
                    # Update the exercise
                    ex.answer = corrected_answer
                    ex.solution_steps = corrected_steps
                    self.save_session()
                    console.print(f"[green]✓ Упражнение {exercise_id} исправлено[/green]")
                    return True
        
        console.print(f"[yellow]Упражнение {exercise_id} не найдено[/yellow]")
        return False
