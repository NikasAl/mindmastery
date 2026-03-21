#!/usr/bin/env python3
"""CLI interface for Mental Mastery application."""

import os
import sys
import uuid
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown
from rich.syntax import Syntax

from llm import LLMClient
from core import TaskDecomposer
from models import TaskDecomposition, Exercise, Difficulty
from visualization import MarkdownRenderer
from storage import ProgressStorage

console = Console()


class MentalMasteryCLI:
    """Main CLI application class."""

    def __init__(self):
        self.llm_client: Optional[LLMClient] = None
        self.decomposer: Optional[TaskDecomposer] = None
        self.renderer = MarkdownRenderer()
        self.storage = ProgressStorage()
        self.current_task: Optional[TaskDecomposition] = None
        self.current_task_id: Optional[str] = None

    def initialize(self):
        """Initialize LLM client and decomposer."""
        # Check for demo mode
        demo_mode = os.getenv("MENTAL_MASTERY_DEMO", "").lower() in ("1", "true", "yes")
        
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key and not demo_mode:
            console.print(Panel(
                "[yellow]OPENROUTER_API_KEY environment variable not set.[/yellow]\n\n"
                "Options:\n"
                "1. Set OPENROUTER_API_KEY from https://openrouter.ai/keys\n"
                "2. Run in demo mode: export MENTAL_MASTERY_DEMO=1\n\n"
                "[dim]Demo mode uses pre-defined decompositions.[/dim]",
                title="⚠️ API Key Required",
                border_style="yellow"
            ))
            choice = Prompt.ask("Enter API key, or 'demo' for demo mode", default="demo")
            
            if choice.lower() == "demo":
                demo_mode = True
            else:
                api_key = choice

        self.demo_mode = demo_mode
        
        if demo_mode:
            console.print("[green]✓ Running in demo mode[/green]")
            return

        try:
            self.llm_client = LLMClient(api_key=api_key)
            self.decomposer = TaskDecomposer(self.llm_client)
            console.print("[green]✓ LLM client initialized[/green]")
        except Exception as e:
            console.print(f"[red]Failed to initialize LLM client: {e}[/red]")
            sys.exit(1)

    def show_welcome(self):
        """Display welcome screen."""
        console.clear()
        console.print(Panel(
            """
[bold cyan]🧠 Mental Mastery[/bold cyan]

Develop your mental calculation skills through intelligent task decomposition.

[italic]Learn to solve complex problems entirely in your mind![/italic]

Features:
• Decomposes complex tasks into trainable skills
• Generates progressive exercises for each skill
• Tracks your progress and mastery
• Teaches mnemonics and visualization techniques
            """,
            border_style="cyan",
            padding=(1, 2)
        ))
        console.print()

    def show_main_menu(self) -> str:
        """Display main menu and get user choice."""
        mode_str = " [dim](demo mode)[/dim]" if getattr(self, 'demo_mode', False) else ""
        
        table = Table(show_header=False, box=None)
        table.add_column("Option", style="cyan", width=4)
        table.add_column("Description")

        table.add_row("1", "📝 Enter new task to decompose")
        table.add_row("2", "📚 Load example tasks")
        if not getattr(self, 'demo_mode', False):
            table.add_row("3", "📊 View progress statistics")
            table.add_row("4", "📂 Open output directory")
            table.add_row("5", "⚙️ Settings")
        else:
            table.add_row("3", "🎮 Demo mode examples")
        table.add_row("q", "🚪 Quit")

        console.print(Panel(table, title=f"🧠 Mental Mastery{mode_str}"))
        console.print()

        if getattr(self, 'demo_mode', False):
            return Prompt.ask("Choose option", choices=["1", "2", "3", "q"], default="2")
        return Prompt.ask("Choose option", choices=["1", "2", "3", "4", "5", "q"], default="1")

    def get_example_tasks(self) -> dict:
        """Return dictionary of example tasks."""
        return {
            "1": {
                "name": "Сканави: Дробное выражение",
                "type": "math",
                "task": r"\frac{(7 - 6,35) : 6,5 + 9,9}{\left(1,2 : 36 + 1,2 : 0,25 - 1\frac{5}{16}\right) : \frac{169}{24}}",
            },
            "2": {
                "name": "Текстовая задача: Половина — треть",
                "type": "word",
                "task": "Половина — треть некоторого числа. Какое это число?",
            },
            "3": {
                "name": "Алгебраическое выражение",
                "type": "math",
                "task": r"\left( \frac{bx+4+\frac{4}{bx}}{2b+(b^2-4)x-2bx^2} + \frac{(4x^2-b^2)\frac{1}{b}}{(b+2x)^2-8bx} \right) \frac{bx}{2}",
            },
            "4": {
                "name": "Упрощение выражения с корнями",
                "type": "math",
                "task": r"\sqrt{11 + 6\sqrt{2}} - \sqrt{11 - 6\sqrt{2}}",
            },
            "5": {
                "name": "Тригонометрическое упрощение",
                "type": "math",
                "task": r"\frac{\sin 3\alpha}{\sin \alpha} - \frac{\cos 3\alpha}{\cos \alpha}",
            },
            "6": {
                "name": "Физика: Свободное падение",
                "type": "physics",
                "task": "Тело брошено вертикально вверх со скоростью 20 м/с. Через сколько времени оно будет на высоте 15 м? (g = 10 м/с²)",
            },
        }

    def select_example_task(self) -> tuple:
        """Let user select an example task."""
        examples = self.get_example_tasks()

        table = Table(title="📚 Example Tasks")
        table.add_column("#", style="cyan", width=3)
        table.add_column("Name", style="green")
        table.add_column("Type", style="yellow")

        for key, task in examples.items():
            table.add_row(key, task["name"], task["type"])

        console.print(table)
        console.print()

        choice = Prompt.ask("Select task (or 'c' to cancel)", choices=list(examples.keys()) + ["c"])
        if choice == "c":
            return None, None, None

        selected = examples[choice]
        return selected["task"], selected["type"], selected["name"]

    def enter_custom_task(self) -> tuple:
        """Let user enter a custom task."""
        console.print(Panel(
            "Enter your task in one of these formats:\n"
            "• LaTeX formula (e.g., \\frac{{a}}{{b}})\n"
            "• Plain text description\n"
            "• Or just describe what you want to learn",
            title="📝 New Task",
            border_style="cyan"
        ))

        task_type = Prompt.ask(
            "Task type",
            choices=["math", "word", "physics"],
            default="math"
        )

        console.print("\n[dim]Enter your task (Ctrl+D or empty line to finish):[/dim]")
        lines = []
        try:
            while True:
                line = input()
                if not line:
                    break
                lines.append(line)
        except EOFError:
            pass

        task = "\n".join(lines).strip()
        if not task:
            console.print("[red]No task entered.[/red]")
            return None, None, None

        return task, task_type, "Custom Task"

    def decompose_task(self, task: str, task_type: str):
        """Decompose a task into skills and exercises."""
        if getattr(self, 'demo_mode', False):
            self._decompose_task_demo(task, task_type)
            return
            
        console.print()
        console.print(Panel(f"[bold]{task}[/bold]", title="📋 Analyzing Task", border_style="cyan"))

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task("Decomposing task and generating exercises...", total=None)
                self.current_task = self.decomposer.decompose(task, task_type)

            self.current_task_id = str(uuid.uuid4())[:8]

            # Save to progress
            self.storage.add_task(self.current_task)

            # Show summary
            self.show_decomposition_summary()

            # Save markdown
            md_path = self.renderer.render_task_decomposition(
                self.current_task, self.current_task_id
            )
            console.print(f"\n[green]📄 Full decomposition saved to: {md_path}[/green]")

        except Exception as e:
            console.print(f"[red]Error during decomposition: {e}[/red]")
            console.print_exception()

    def _decompose_task_demo(self, task: str, task_type: str):
        """Decompose task in demo mode using pre-defined examples."""
        from demo import DEMO_DECOMPOSITIONS, generate_demo_exercises
        
        console.print("\n[yellow]Demo mode: Using pre-defined decomposition[/yellow]\n")
        
        # Find matching demo or use default
        demo_data = None
        for key, data in DEMO_DECOMPOSITIONS.items():
            if data["original_task"] in task or data["original_task_plain"] in task:
                demo_data = data
                break
        
        if not demo_data:
            # Default to fraction for demo
            demo_data = DEMO_DECOMPOSITIONS["fraction"]
        
        # Convert to TaskDecomposition
        from models import Skill, SkillCategory, Exercise, Difficulty
        
        skills = []
        for s in demo_data["skills"]:
            skills.append(Skill(
                id=s["id"],
                name=s["name"],
                description=s["description"],
                category=SkillCategory(s["category"].lower()),
                difficulty_base=s["difficulty_base"],
                cognitive_load=s["cognitive_load"],
                prerequisites=s.get("prerequisites", []),
                tips=s.get("tips", []),
                mnemonics=s.get("mnemonics")
            ))
        
        exercises = {}
        for skill in skills:
            ex_data = generate_demo_exercises(skill.id)
            exercises[skill.id] = [
                Exercise(
                    id=f"ex_{skill.id}_{i}",
                    skill_id=skill.id,
                    level=Difficulty(ex.get("level", "intro")),
                    question=ex["question"],
                    question_plain=ex["question_plain"],
                    answer=ex["answer"],
                    solution_steps=[ex["answer"]],
                    hints=[],
                    time_estimate=30,
                    cognitive_load=3
                )
                for i, ex in enumerate(ex_data)
            ]
        
        self.current_task = TaskDecomposition(
            original_task=demo_data["original_task"],
            original_task_plain=demo_data["original_task_plain"],
            full_solution=demo_data["full_solution"],
            skills=skills,
            skill_graph=demo_data["skill_graph"],
            exercises=exercises,
            estimated_total_time=15
        )
        self.current_task_id = str(uuid.uuid4())[:8]
        
        self.show_decomposition_summary()

    def show_decomposition_summary(self):
        """Show summary of task decomposition."""
        if not self.current_task:
            return

        task = self.current_task

        # Skills table
        table = Table(title=f"🎯 Identified Skills ({len(task.skills)} total)")
        table.add_column("#", width=3)
        table.add_column("Skill", style="green")
        table.add_column("Category", style="cyan")
        table.add_column("Difficulty", style="yellow")
        table.add_column("Cognitive Load", style="magenta")
        table.add_column("Exercises", style="blue")

        for i, skill in enumerate(task.skills, 1):
            ex_count = len(task.exercises.get(skill.id, []))
            table.add_row(
                str(i),
                skill.name,
                skill.category.value,
                "⭐" * skill.difficulty_base,
                "🧠" * skill.cognitive_load,
                str(ex_count)
            )

        console.print(table)

        # Solution steps
        console.print("\n[bold]📝 Solution Steps:[/bold]")
        for i, step in enumerate(task.full_solution, 1):
            console.print(f"  {i}. {step}")

        # Estimated time
        console.print(f"\n⏱️ Estimated training time: [bold]{task.estimated_total_time}[/bold] minutes")

    def practice_task(self):
        """Start practice session for current task."""
        if not self.current_task:
            console.print("[yellow]No task loaded. Decompose a task first.[/yellow]")
            return

        console.print("\n[bold cyan]🎯 Practice Mode[/bold cyan]")
        console.print("Select a skill to practice:")

        for i, skill in enumerate(self.current_task.skills, 1):
            ex_count = len(self.current_task.exercises.get(skill.id, []))
            console.print(f"  {i}. {skill.name} ({ex_count} exercises)")

        choice = Prompt.ask("Select skill number (or 'q' to quit)")
        if choice.lower() == 'q':
            return

        try:
            skill_idx = int(choice) - 1
            if 0 <= skill_idx < len(self.current_task.skills):
                self.practice_skill(self.current_task.skills[skill_idx])
            else:
                console.print("[red]Invalid selection[/red]")
        except ValueError:
            console.print("[red]Please enter a number[/red]")

    def practice_skill(self, skill):
        """Practice a specific skill."""
        exercises = self.current_task.exercises.get(skill.id, [])

        if not exercises:
            console.print(f"[yellow]No exercises available for {skill.name}[/yellow]")
            return

        # Group by level
        by_level = {}
        for ex in exercises:
            by_level.setdefault(ex.level, []).append(ex)

        console.print(f"\n[bold]{skill.name}[/bold]")
        console.print(f"[dim]{skill.description}[/dim]")

        if skill.tips:
            console.print("\n[bold]Tips:[/bold]")
            for tip in skill.tips:
                console.print(f"  💡 {tip}")

        if skill.mnemonics:
            console.print(f"\n[bold]🧩 Mnemonic:[/bold] {skill.mnemonics}")

        # Select difficulty level
        levels = list(by_level.keys())
        console.print("\n[bold]Select difficulty level:[/bold]")
        for i, level in enumerate(levels, 1):
            console.print(f"  {i}. {level.value} ({len(by_level[level])} exercises)")

        choice = Prompt.ask("Select level")
        try:
            level_idx = int(choice) - 1
            if 0 <= level_idx < len(levels):
                self.practice_exercises(by_level[levels[level_idx]], skill)
        except ValueError:
            console.print("[red]Invalid selection[/red]")

    def practice_exercises(self, exercises: list, skill):
        """Run through exercises for a skill."""
        for i, ex in enumerate(exercises, 1):
            console.print(f"\n{'='*60}")
            console.print(f"[bold cyan]Exercise {i}/{len(exercises)}[/bold cyan] [dim]({ex.level.value})[/dim]")
            console.print(f"⏱️ Time estimate: {ex.time_estimate}s")
            console.print()

            # Show question
            console.print(Panel(
                f"$$ {ex.question} $$\n\n[dim]{ex.question_plain}[/dim]",
                title="📝 Question",
                border_style="cyan"
            ))

            # Option to open in browser for better rendering
            if Confirm.ask("Open in browser for better LaTeX rendering?", default=False):
                md_path = self.renderer.render_practice_session(
                    ex, skill.name, self.current_task_id
                )
                self.renderer.open_in_browser(md_path)

            # Practice loop
            while True:
                action = Prompt.ask(
                    "Action",
                    choices=["answer", "hint", "skip", "quit"],
                    default="answer"
                )

                if action == "quit":
                    return
                elif action == "skip":
                    self.show_answer(ex)
                    break
                elif action == "hint":
                    for j, hint in enumerate(ex.hints, 1):
                        if Confirm.ask(f"Show hint {j}?", default=True):
                            console.print(f"  💡 [yellow]{hint}[/yellow]")
                        else:
                            break
                elif action == "answer":
                    user_answer = Prompt.ask("Your answer")
                    self.check_answer(ex, user_answer)
                    break

    def show_answer(self, ex: Exercise):
        """Show the correct answer and solution."""
        console.print(Panel(
            f"[green]Answer: {ex.answer}[/green]\n\n"
            + "\n".join(f"  {i+1}. {s}" for i, s in enumerate(ex.solution_steps)),
            title="✅ Solution",
            border_style="green"
        ))

    def check_answer(self, ex: Exercise, user_answer: str):
        """Check user's answer."""
        # Normalize answers
        correct = user_answer.strip().lower() == ex.answer.strip().lower()

        if correct:
            console.print("\n[green]✓ Correct![/green]")
            self.storage.update_progress(
                self.current_task_id,
                ex.skill_id,
                correct=True,
                exercise_time=ex.time_estimate
            )
        else:
            console.print(f"\n[red]✗ Incorrect. Correct answer: {ex.answer}[/red]")
            self.storage.update_progress(
                self.current_task_id,
                ex.skill_id,
                correct=False,
                exercise_time=ex.time_estimate
            )

        self.show_answer(ex)

    def show_progress(self):
        """Show user progress statistics."""
        stats = self.storage.get_stats()

        table = Table(title="📊 Your Progress")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Tasks", str(stats["total_tasks"]))
        table.add_row("Total Exercises", str(stats["total_exercises"]))
        table.add_row("Accuracy", f"{stats['accuracy']:.1f}%")
        table.add_row("Completed Tasks", str(stats["completed_tasks"]))

        console.print(table)

        # Show tasks in progress
        session = self.storage.load_session()
        if session.tasks:
            console.print("\n[bold]Tasks in Progress:[/bold]")
            for task_id, task in session.tasks.items():
                status = "✅ Ready to solve original" if task.can_solve_original else "🔄 In progress"
                console.print(f"  {status} {task_id}: {len(task.skill_progress)} skills")

    def open_output_directory(self):
        """Open output directory in file manager."""
        import subprocess

        output_dir = self.renderer.output_dir
        console.print(f"[cyan]Output directory: {output_dir}[/cyan]")

        if output_dir.exists():
            # Try to open with default file manager
            try:
                if sys.platform == "linux":
                    subprocess.Popen(["xdg-open", str(output_dir)])
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", str(output_dir)])
                elif sys.platform == "win32":
                    subprocess.Popen(["explorer", str(output_dir)])
                console.print("[green]✓ Opened file manager[/green]")
            except Exception as e:
                console.print(f"[yellow]Could not open file manager: {e}[/yellow]")
                console.print(f"Path: {output_dir}")

    def run(self):
        """Main application loop."""
        self.show_welcome()
        self.initialize()

        while True:
            console.print()
            choice = self.show_main_menu()

            if choice == "q":
                console.print("\n[cyan]Thanks for using Mental Mastery! 🧠[/cyan]\n")
                break
            elif choice == "1":
                task, task_type, name = self.enter_custom_task()
                if task:
                    self.decompose_task(task, task_type)
                    if self.current_task and Confirm.ask("\nStart practicing now?", default=True):
                        self.practice_task()
            elif choice == "2":
                task, task_type, name = self.select_example_task()
                if task:
                    self.decompose_task(task, task_type)
                    if self.current_task and Confirm.ask("\nStart practicing now?", default=True):
                        self.practice_task()
            elif choice == "3":
                if getattr(self, 'demo_mode', False):
                    # Run demo examples
                    from demo import run_demo
                    run_demo()
                else:
                    self.show_progress()
            elif choice == "4":
                self.open_output_directory()
            elif choice == "5":
                self.show_settings()

    def show_settings(self):
        """Show settings menu."""
        console.print(Panel(
            f"""
[cyan]Current Settings[/cyan]

LLM Model: {self.llm_client.model if self.llm_client else 'Not set'}
Output Directory: {self.renderer.output_dir}
Cache Directory: {self.decomposer.cache_dir if self.decomposer else 'Not set'}

[dim]Settings are configured via environment variables:
  OPENROUTER_API_KEY - Your API key
  MENTAL_MASTERY_MODEL - Model to use (default: claude-3.5-sonnet)[/dim]
            """,
            title="⚙️ Settings",
            border_style="yellow"
        ))


def main():
    """Entry point for the CLI."""
    app = MentalMasteryCLI()
    try:
        app.run()
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    main()
