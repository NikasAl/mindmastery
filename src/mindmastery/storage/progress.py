"""Storage module for user progress."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from rich.console import Console

from models import Session, TaskProgress, UserProgress, TaskDecomposition

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
