#!/usr/bin/env python3
"""CLI интерфейс для MindMastery."""

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

from .llm import LLMClient, select_model
from .core import TaskDecomposer
from .models import TaskDecomposition, Exercise, Difficulty, UserProgress
from .visualization import MarkdownRenderer
from .storage import ProgressStorage

console = Console()


class MentalMasteryCLI:
    """Главный класс CLI приложения."""

    def __init__(self):
        self.llm_client: Optional[LLMClient] = None
        self.decomposer: Optional[TaskDecomposer] = None
        self.renderer = MarkdownRenderer()
        self.storage = ProgressStorage()
        self.current_task: Optional[TaskDecomposition] = None
        self.current_task_id: Optional[str] = None

    def initialize(self):
        """Инициализация LLM клиента и декомпозера."""
        demo_mode = os.getenv("MENTAL_MASTERY_DEMO", "").lower() in ("1", "true", "yes")
        
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key and not demo_mode:
            console.print(Panel(
                "[yellow]Переменная OPENROUTER_API_KEY не установлена.[/yellow]\n\n"
                "Варианты:\n"
                "1. Установите OPENROUTER_API_KEY с https://openrouter.ai/keys\n"
                "2. Запустите в демо-режиме: export MENTAL_MASTERY_DEMO=1\n\n"
                "[dim]Демо-режим использует предустановленные примеры.[/dim]",
                title="⚠️ Требуется API ключ",
                border_style="yellow"
            ))
            choice = Prompt.ask("Введите API ключ или 'demo' для демо-режима", default="demo")
            
            if choice.lower() == "demo":
                demo_mode = True
            else:
                api_key = choice

        self.demo_mode = demo_mode
        
        if demo_mode:
            console.print("[green]✓ Запущен демо-режим[/green]")
            return

        try:
            # Select model
            console.print()
            model = select_model()
            
            self.llm_client = LLMClient(api_key=api_key, model=model)
            self.decomposer = TaskDecomposer(self.llm_client)
            console.print(f"[green]✓ LLM клиент инициализирован[/green] (модель: {model})")
        except Exception as e:
            console.print(f"[red]Ошибка инициализации LLM клиента: {e}[/red]")
            sys.exit(1)

    def show_welcome(self):
        """Показать приветственный экран."""
        console.clear()
        console.print(Panel(
            """
[bold cyan]🧠 MindMastery[/bold cyan]

Развивай навыки ментальных вычислений через декомпозицию задач.

[italic]Научись решать сложные задачи в уме![/italic]

Возможности:
• Декомпозиция задач на тренируемые навыки
• Генерация упражнений с нарастающей сложностью
• Отслеживание прогресса и мастерства
• Мнемотехники и методы визуализации
            """,
            border_style="cyan",
            padding=(1, 2)
        ))
        console.print()

    def show_main_menu(self) -> str:
        """Показать главное меню."""
        mode_str = " [dim](демо-режим)[/dim]" if getattr(self, 'demo_mode', False) else ""
        
        table = Table(show_header=False, box=None)
        table.add_column("Опция", style="cyan", width=4)
        table.add_column("Описание")

        table.add_row("1", "📝 Ввести новую задачу")
        table.add_row("2", "📚 Примеры задач")
        if not getattr(self, 'demo_mode', False):
            # Check for in-progress tasks
            session = self.storage.load_session()
            incomplete_count = sum(1 for t in session.tasks.values() if not t.completed and not t.can_solve_original)
            if incomplete_count > 0:
                table.add_row("3", f"▶️  Продолжить задачу ({incomplete_count} в процессе)")
                table.add_row("4", "📊 Статистика прогресса")
                table.add_row("5", "📂 Открыть папку вывода")
                table.add_row("6", "⚙️ Настройки")
            else:
                table.add_row("3", "📊 Статистика прогресса")
                table.add_row("4", "📂 Открыть папку вывода")
                table.add_row("5", "⚙️ Настройки")
        else:
            table.add_row("3", "🎮 Примеры демо-режима")
        table.add_row("q", "🚪 Выход")

        console.print(Panel(table, title=f"🧠 MindMastery{mode_str}"))
        console.print()

        if getattr(self, 'demo_mode', False):
            return Prompt.ask("Выберите опцию", choices=["1", "2", "3", "q"], default="2")
        
        # Dynamic choices based on in-progress tasks
        session = self.storage.load_session()
        incomplete_count = sum(1 for t in session.tasks.values() if not t.completed and not t.can_solve_original)
        if incomplete_count > 0:
            return Prompt.ask("Выберите опцию", choices=["1", "2", "3", "4", "5", "6", "q"], default="1")
        return Prompt.ask("Выберите опцию", choices=["1", "2", "3", "4", "5", "q"], default="1")

    def get_example_tasks(self) -> dict:
        """Вернуть словарь примеров задач."""
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
        """Выбор примера задачи."""
        examples = self.get_example_tasks()

        table = Table(title="📚 Примеры задач")
        table.add_column("#", style="cyan", width=3)
        table.add_column("Название", style="green")
        table.add_column("Тип", style="yellow")

        for key, task in examples.items():
            table.add_row(key, task["name"], task["type"])

        console.print(table)
        console.print()

        choice = Prompt.ask("Выберите задачу (или 'c' для отмены)", choices=list(examples.keys()) + ["c"])
        if choice == "c":
            return None, None, None

        selected = examples[choice]
        return selected["task"], selected["type"], selected["name"]

    def enter_custom_task(self) -> tuple:
        """Ввод пользовательской задачи."""
        console.print(Panel(
            "Введите задачу в одном из форматов:\n"
            "• Формула LaTeX (например, \\frac{{a}}{{b}})\n"
            "• Текстовое описание\n"
            "• Или просто опишите, чему хотите научиться",
            title="📝 Новая задача",
            border_style="cyan"
        ))

        task_type = Prompt.ask(
            "Тип задачи",
            choices=["math", "word", "physics"],
            default="math"
        )

        console.print("\n[dim]Введите задачу (Ctrl+D или пустая строка для завершения):[/dim]")
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
            console.print("[red]Задача не введена.[/red]")
            return None, None, None

        return task, task_type, "Пользовательская задача"

    def decompose_task(self, task: str, task_type: str):
        """Декомпозиция задачи на навыки и упражнения."""
        if getattr(self, 'demo_mode', False):
            self._decompose_task_demo(task, task_type)
            return
            
        console.print()
        console.print(Panel(f"[bold]{task}[/bold]", title="📋 Анализ задачи", border_style="cyan"))

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task("Декомпозиция задачи и генерация упражнений...", total=None)
                self.current_task = self.decomposer.decompose(task, task_type)

            task_progress = self.storage.add_task(self.current_task)
            self.current_task_id = task_progress.task_id
            self.show_decomposition_summary()

            md_path = self.renderer.render_task_decomposition(
                self.current_task, self.current_task_id
            )
            console.print(f"\n[green]📄 Декомпозиция сохранена: {md_path}[/green]")

        except Exception as e:
            console.print(f"[red]Ошибка при декомпозиции: {e}[/red]")
            console.print_exception()

    def _decompose_task_demo(self, task: str, task_type: str):
        """Декомпозиция в демо-режиме."""
        from .demo import DEMO_DECOMPOSITIONS, generate_demo_exercises
        
        console.print("\n[yellow]Демо-режим: Использование предустановленной декомпозиции[/yellow]\n")
        
        demo_data = None
        for key, data in DEMO_DECOMPOSITIONS.items():
            if data["original_task"] in task or data["original_task_plain"] in task:
                demo_data = data
                break
        
        if not demo_data:
            demo_data = DEMO_DECOMPOSITIONS["fraction"]
        
        from .models import Skill, SkillCategory, Exercise, Difficulty
        
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
        """Показать сводку декомпозиции."""
        if not self.current_task:
            return

        task = self.current_task

        table = Table(title=f"🎯 Выявленные навыки ({len(task.skills)} шт.)")
        table.add_column("#", width=3)
        table.add_column("Навык", style="green")
        table.add_column("Категория", style="cyan")
        table.add_column("Сложность", style="yellow")
        table.add_column("Нагрузка", style="magenta")
        table.add_column("Упражнения", style="blue")

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

        console.print("\n[bold]📝 Шаги решения:[/bold]")
        for i, step in enumerate(task.full_solution, 1):
            console.print(f"  {i}. {step}")

        console.print(f"\n⏱️ Оценочное время тренировки: [bold]{task.estimated_total_time}[/bold] минут")

    def practice_task(self):
        """Начать практику по текущей задаче."""
        if not self.current_task:
            console.print("[yellow]Задача не загружена. Сначала выполните декомпозицию.[/yellow]")
            return

        console.print("\n[bold cyan]🎯 Режим практики[/bold cyan]")
        console.print("[dim]Упражнения генерируются по требованию для экономии токенов[/dim]")
        console.print("Выберите навык для тренировки:")

        for i, skill in enumerate(self.current_task.skills, 1):
            # Check if exercises are cached
            cached_ex = self.storage.get_exercises_for_skill(self.current_task_id, skill.id)
            if cached_ex:
                ex_count = len(cached_ex)
                status = "✅"
            else:
                # Check in current task
                ex_count = len(self.current_task.exercises.get(skill.id, []))
                status = "✅" if ex_count > 0 else "⚡"
            
            console.print(f"  {i}. {status} {skill.name} ({ex_count} упр.)" if ex_count > 0 else f"  {i}. {status} {skill.name} (генерация...)")

        choice = Prompt.ask("Выберите номер навыка (или 'q' для выхода)")
        if choice.lower() == 'q':
            return

        try:
            skill_idx = int(choice) - 1
            if 0 <= skill_idx < len(self.current_task.skills):
                self.practice_skill(self.current_task.skills[skill_idx])
            else:
                console.print("[red]Неверный выбор[/red]")
        except ValueError:
            console.print("[red]Введите число[/red]")

    def practice_skill(self, skill, start_level_idx: int = 0):
        """Практика конкретного навыка с автоматическим переходом на следующий уровень."""
        
        # Check if exercises exist (lazy generation)
        exercises = self.current_task.exercises.get(skill.id, [])
        
        if not exercises:
            # Try to load from storage cache
            exercises = self.storage.get_exercises_for_skill(self.current_task_id, skill.id)
            
        if not exercises:
            # Need to generate exercises on-demand
            console.print(f"\n[yellow]⚡ Генерация упражнений для: {skill.name}...[/yellow]")
            
            if getattr(self, 'demo_mode', False):
                # Use demo exercises
                from .demo import generate_demo_exercises
                ex_data = generate_demo_exercises(skill.id)
                from .models import Exercise, Difficulty
                exercises = [
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
            else:
                # Generate via LLM
                exercises = self.decomposer.generate_exercises_for_skill(skill, self.current_task)
            
            # Cache the exercises
            if exercises:
                self.storage.store_exercises_for_skill(self.current_task_id, skill.id, exercises)
                # Also update current_task
                self.current_task.exercises[skill.id] = exercises
            else:
                console.print(f"[red]Не удалось сгенерировать упражнения для {skill.name}[/red]")
                return

        by_level = {}
        for ex in exercises:
            by_level.setdefault(ex.level, []).append(ex)

        levels = list(by_level.keys())
        
        console.print(f"\n[bold]{skill.name}[/bold]")
        console.print(f"[dim]{skill.description}[/dim]")

        if skill.tips:
            console.print("\n[bold]Советы:[/bold]")
            for tip in skill.tips:
                console.print(f"  💡 {tip}")

        if skill.mnemonics:
            console.print(f"\n[bold]🧩 Мнемотехника:[/bold] {skill.mnemonics}")

        # Start from specified level or let user choose
        current_level_idx = start_level_idx
        
        while current_level_idx < len(levels):
            level = levels[current_level_idx]
            
            console.print(f"\n[bold cyan]📍 Уровень: {level.value.upper()}[/bold cyan]")
            console.print("\n[bold]Выберите действие:[/bold]")
            console.print(f"  1. Начать уровень {level.value} ({len(by_level[level])} упражнений)")
            if current_level_idx < len(levels) - 1:
                console.print(f"  2. Пропустить и перейти к уровню {levels[current_level_idx + 1].value}")
            console.print("  q. Вернуться к выбору навыка")
            
            choice = Prompt.ask("Выбор", default="1")
            
            if choice.lower() == 'q':
                return
            elif choice == "2" and current_level_idx < len(levels) - 1:
                current_level_idx += 1
                continue
            elif choice == "1":
                # Practice this level
                completed = self.practice_exercises(by_level[level], skill)
                
                if not completed:  # User quit
                    return
                
                # Show progress after level
                self.show_skill_progress(skill)
                
                # Offer next level
                if current_level_idx < len(levels) - 1:
                    next_level = levels[current_level_idx + 1]
                    if Confirm.ask(f"\n🎯 Перейти к уровню {next_level.value}?", default=True):
                        current_level_idx += 1
                    else:
                        # Offer to practice another skill
                        if Confirm.ask("Выбрать другой навык?", default=True):
                            self.practice_task()
                            return
                        return
                else:
                    console.print("\n[green]🎉 Все уровни этого навыка пройдены![/green]")
                    if Confirm.ask("Выбрать другой навык?", default=True):
                        self.practice_task()
                        return
                    return
            else:
                console.print("[red]Неверный выбор[/red]")
    
    def show_skill_progress(self, skill):
        """Показать прогресс по конкретному навыку."""
        session = self.storage.load_session()
        
        if self.current_task_id not in session.tasks:
            return
        
        task = session.tasks[self.current_task_id]
        
        if skill.id not in task.skill_progress:
            return
        
        progress = task.skill_progress[skill.id]
        
        console.print(Panel(
            f"[cyan]Навык:[/cyan] {skill.name}\n"
            f"[cyan]Упражнений выполнено:[/cyan] {progress.exercises_completed}\n"
            f"[cyan]Правильных ответов:[/cyan] {progress.exercises_correct}\n"
            f"[cyan]Текущая серия:[/cyan] {progress.streak}\n"
            f"[cyan]Уровень мастерства:[/cyan] {progress.mastery_score * 100:.0f}%",
            title="📊 Прогресс навыка",
            border_style="green"
        ))

    def practice_exercises(self, exercises: list, skill) -> bool:
        """Пройти упражнения. Возвращает True если все пройдены, False если выход через quit."""
        # Ask about browser once at the start
        open_in_browser = Confirm.ask("Открыть в браузере для лучшего рендеринга LaTeX?", default=False)
        
        for i, ex in enumerate(exercises, 1):
            console.print(f"\n{'='*60}")
            console.print(f"[bold cyan]Упражнение {i}/{len(exercises)}[/bold cyan] [dim]({ex.level.value})[/dim]")
            console.print(f"⏱️ Оценка времени: {ex.time_estimate}с")
            console.print()

            console.print(Panel(
                f"$$ {ex.question} $$\n\n[dim]{ex.question_plain}[/dim]",
                title="📝 Вопрос",
                border_style="cyan"
            ))

            if open_in_browser:
                md_path = self.renderer.render_practice_session(
                    ex, skill.name, self.current_task_id
                )
                self.renderer.open_in_browser(md_path)

            while True:
                action = Prompt.ask(
                    "Действие",
                    choices=["answer", "hint", "skip", "quit"],
                    default="answer"
                )

                if action == "quit":
                    return False
                elif action == "skip":
                    self.show_answer(ex)
                    break
                elif action == "hint":
                    for j, hint in enumerate(ex.hints, 1):
                        if Confirm.ask(f"Показать подсказку {j}?", default=True):
                            console.print(f"  💡 [yellow]{hint}[/yellow]")
                        else:
                            break
                elif action == "answer":
                    user_answer = Prompt.ask("Ваш ответ")
                    self.check_answer(ex, user_answer)
                    break
        
        return True

    def show_answer(self, ex: Exercise):
        """Показать правильный ответ."""
        console.print(Panel(
            f"[green]Ответ: {ex.answer}[/green]\n\n"
            + "\n".join(f"  {i+1}. {s}" for i, s in enumerate(ex.solution_steps)),
            title="✅ Решение",
            border_style="green"
        ))

    def check_answer(self, ex: Exercise, user_answer: str):
        """Проверить ответ пользователя."""
        correct = user_answer.strip().lower() == ex.answer.strip().lower()

        if correct:
            console.print("\n[green]✓ Правильно![/green]")
            self.storage.update_progress(
                self.current_task_id,
                ex.skill_id,
                correct=True,
                exercise_time=ex.time_estimate
            )
        else:
            console.print(f"\n[red]✗ Неправильно. Правильный ответ: {ex.answer}[/red]")
            self.storage.update_progress(
                self.current_task_id,
                ex.skill_id,
                correct=False,
                exercise_time=ex.time_estimate
            )

        self.show_answer(ex)

    def show_progress(self):
        """Показать детальную статистику прогресса с роадмапом."""
        session = self.storage.load_session()
        stats = self.storage.get_stats()

        # Overall stats summary
        console.print(Panel(
            f"[cyan]Всего задач:[/cyan] {stats['total_tasks']}\n"
            f"[cyan]Всего упражнений:[/cyan] {stats['total_exercises']}\n"
            f"[cyan]Точность:[/cyan] {stats['accuracy']:.1f}%\n"
            f"[cyan]Завершено задач:[/cyan] {stats['completed_tasks']}",
            title="📊 Общая статистика",
            border_style="cyan"
        ))

        if not session.tasks:
            console.print("\n[yellow]Нет задач для отображения.[/yellow]")
            return

        # Detailed roadmap for each task
        for task_id, task in session.tasks.items():
            self._show_task_roadmap(task_id, task)
    
    def _show_task_roadmap(self, task_id: str, task):
        """Показать детальный роадмап по задаче."""
        decomposition = task.decomposition
        
        # Task header
        status_icon = "✅" if task.can_solve_original else "🔄"
        status_text = "ГОТОВ К РЕШЕНИЮ" if task.can_solve_original else "В ПРОЦЕССЕ"
        
        console.print(f"\n[bold cyan]{'═'*70}[/bold cyan]")
        console.print(f"[bold]{status_icon} Задача {task_id}[/bold] [{status_text}]")
        console.print(f"[dim]{decomposition.original_task_plain[:80]}{'...' if len(decomposition.original_task_plain) > 80 else ''}[/dim]")
        console.print(f"[bold cyan]{'═'*70}[/bold cyan]")
        
        # Count mastered skills
        mastered_count = sum(1 for p in task.skill_progress.values() if p.mastery_score >= 0.8)
        total_skills = len(decomposition.skills)
        
        # Overall progress bar
        progress_pct = mastered_count / total_skills if total_skills > 0 else 0
        bar_width = 40
        filled = int(bar_width * progress_pct)
        empty = bar_width - filled
        progress_bar = "█" * filled + "░" * empty
        
        console.print(f"\n[bold]Общий прогресс:[/bold] [{progress_bar}] {progress_pct*100:.0f}% ({mastered_count}/{total_skills} навыков)")
        
        # Get skill order from graph
        skill_order = decomposition.skill_graph.get("order", [s.id for s in decomposition.skills])
        
        # Roadmap table
        console.print(f"\n[bold]🗺️  РОАДМАП НАВЫКОВ:[/bold]\n")
        
        for i, skill_id in enumerate(skill_order, 1):
            skill = next((s for s in decomposition.skills if s.id == skill_id), None)
            if not skill:
                continue
            
            progress = task.skill_progress.get(skill_id)
            
            # Determine status
            if progress and progress.mastery_score >= 0.8:
                status = "✅"
                status_color = "green"
            elif progress and progress.exercises_completed > 0:
                status = "🔄"
                status_color = "yellow"
            else:
                status = "⏳"
                status_color = "dim"
            
            # Current position marker
            current_marker = "▶️ " if progress and 0 < progress.mastery_score < 0.8 else "   "
            
            # Skill name with category
            skill_name = f"{skill.name}"
            category = f"[dim]({skill.category.value})[/dim]"
            
            # Exercises progress
            total_ex = len(decomposition.exercises.get(skill_id, []))
            completed_ex = progress.exercises_completed if progress else 0
            correct_ex = progress.exercises_correct if progress else 0
            
            ex_progress = f"{completed_ex}/{total_ex} упр."
            
            # Mastery percentage
            mastery_pct = progress.mastery_score * 100 if progress else 0
            
            # Mini progress bar for skill
            mini_width = 10
            mini_filled = int(mini_width * (mastery_pct / 100))
            mini_empty = mini_width - mini_filled
            mini_bar = f"[{'█'*mini_filled}{'░'*mini_empty}]"
            
            # Prerequisites check
            prereqs = decomposition.skill_graph.get(skill_id, [])
            prereq_ok = all(
                task.skill_progress.get(p, UserProgress(skill_id=p)).mastery_score >= 0.8
                for p in prereqs
            ) if prereqs else True
            
            lock_icon = "🔒" if not prereq_ok and (not progress or progress.exercises_completed == 0) else ""
            
            # Print skill row
            console.print(f"{current_marker}[{status_color}]{status}[/{status_color}] {i}. {skill_name} {category}")
            console.print(f"      {ex_progress} | Мастерство: {mini_bar} {mastery_pct:.0f}% {lock_icon}")
            
            if progress and progress.streak > 0:
                console.print(f"      [dim]🔥 Серия: {progress.streak}[/dim]")
        
        # Summary footer
        console.print(f"\n[bold cyan]{'─'*70}[/bold cyan]")
        
        total_exercises = sum(len(ex) for ex in decomposition.exercises.values())
        total_completed = sum(p.exercises_completed for p in task.skill_progress.values())
        total_correct = sum(p.exercises_correct for p in task.skill_progress.values())
        
        console.print(
            f"📊 Итого: {total_completed}/{total_exercises} упражнений | "
            f"Точность: {total_correct/total_completed*100:.0f}%" if total_completed > 0 else "📊 Начните тренировку!"
        )
        
        # Next recommended action
        if not task.can_solve_original:
            next_skill_id = task.get_next_skill()
            if next_skill_id:
                next_skill = next((s for s in decomposition.skills if s.id == next_skill_id), None)
                if next_skill:
                    console.print(f"\n[bold green]🎯 Рекомендуемый следующий навык: {next_skill.name}[/bold green]")
        else:
            console.print(f"\n[bold green]🎉 Поздравляем! Вы готовы решить оригинальную задачу![/bold green]")

    def open_output_directory(self):
        """Открыть папку вывода."""
        import subprocess

        output_dir = self.renderer.output_dir
        console.print(f"[cyan]Папка вывода: {output_dir}[/cyan]")

        if output_dir.exists():
            try:
                if sys.platform == "linux":
                    subprocess.Popen(["xdg-open", str(output_dir)])
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", str(output_dir)])
                elif sys.platform == "win32":
                    subprocess.Popen(["explorer", str(output_dir)])
                console.print("[green]✓ Открыт файловый менеджер[/green]")
            except Exception as e:
                console.print(f"[yellow]Не удалось открыть: {e}[/yellow]")
                console.print(f"Путь: {output_dir}")

    def resume_task(self):
        """Продолжить незавершенную задачу."""
        session = self.storage.load_session()
        
        # Filter incomplete tasks
        incomplete_tasks = [
            (task_id, task) 
            for task_id, task in session.tasks.items() 
            if not task.completed and not task.can_solve_original
        ]
        
        if not incomplete_tasks:
            console.print("[yellow]Нет задач в процессе.[/yellow]")
            return
        
        console.print("\n[bold cyan]▶️  Продолжить задачу[/bold cyan]")
        
        table = Table()
        table.add_column("#", style="cyan", width=3)
        table.add_column("Задача", style="green")
        table.add_column("Прогресс", style="yellow")
        table.add_column("Мастерство", style="magenta")
        
        for i, (task_id, task) in enumerate(incomplete_tasks, 1):
            # Calculate progress
            total_skills = len(task.skill_progress)
            mastered_skills = sum(1 for p in task.skill_progress.values() if p.mastery_score >= 0.8)
            
            # Get task preview
            task_preview = task.decomposition.original_task_plain[:50]
            if len(task.decomposition.original_task_plain) > 50:
                task_preview += "..."
            
            progress_str = f"{mastered_skills}/{total_skills} навыков"
            
            # Average mastery
            if task.skill_progress:
                avg_mastery = sum(p.mastery_score for p in task.skill_progress.values()) / len(task.skill_progress)
                mastery_str = f"{avg_mastery*100:.0f}%"
            else:
                mastery_str = "0%"
            
            table.add_row(str(i), task_preview, progress_str, mastery_str)
        
        console.print(table)
        
        choice = Prompt.ask(
            f"\nВыберите задачу (1-{len(incomplete_tasks)}) или 'c' для отмены",
            default="1"
        )
        
        if choice.lower() == 'c':
            return
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(incomplete_tasks):
                task_id, task_progress = incomplete_tasks[idx]
                
                # Load the task
                self.current_task = task_progress.decomposition
                self.current_task_id = task_id
                
                console.print(f"\n[green]✓ Загружена задача: {task_id}[/green]")
                
                # Show summary
                self.show_decomposition_summary()
                
                # Start practice
                if Confirm.ask("\nНачать практику?", default=True):
                    self.practice_task()
            else:
                console.print("[red]Неверный выбор[/red]")
        except ValueError:
            if choice.lower() != 'c':
                console.print("[red]Введите число[/red]")

    def run(self):
        """Главный цикл приложения."""
        self.show_welcome()
        self.initialize()

        while True:
            console.print()
            choice = self.show_main_menu()
            
            # Check if there are in-progress tasks to adjust menu handling
            session = self.storage.load_session()
            has_incomplete = any(
                not t.completed and not t.can_solve_original 
                for t in session.tasks.values()
            )

            if choice == "q":
                console.print("\n[cyan]Спасибо за использование MindMastery! 🧠[/cyan]\n")
                break
            elif choice == "1":
                task, task_type, name = self.enter_custom_task()
                if task:
                    self.decompose_task(task, task_type)
                    if self.current_task and Confirm.ask("\nНачать практику?", default=True):
                        self.practice_task()
            elif choice == "2":
                task, task_type, name = self.select_example_task()
                if task:
                    self.decompose_task(task, task_type)
                    if self.current_task and Confirm.ask("\nНачать практику?", default=True):
                        self.practice_task()
            elif choice == "3":
                if getattr(self, 'demo_mode', False):
                    from .demo import run_demo
                    run_demo()
                elif has_incomplete:
                    # Option 3 is "Resume task" when there are incomplete tasks
                    self.resume_task()
                else:
                    self.show_progress()
            elif choice == "4":
                if has_incomplete:
                    # Option 4 is "Progress" when there are incomplete tasks
                    self.show_progress()
                else:
                    self.open_output_directory()
            elif choice == "5":
                if has_incomplete:
                    # Option 5 is "Open output" when there are incomplete tasks
                    self.open_output_directory()
                else:
                    self.show_settings()
            elif choice == "6":
                # Option 6 is "Settings" (only when there are incomplete tasks)
                self.show_settings()

    def show_settings(self):
        """Показать настройки."""
        console.print(Panel(
            f"""
[cyan]Текущие настройки[/cyan]

LLM модель: {self.llm_client.model if self.llm_client else 'Не установлена'}
Папка вывода: {self.renderer.output_dir}
Папка кэша: {self.decomposer.cache_dir if self.decomposer else 'Не установлена'}

[dim]Настройки через переменные окружения:
  OPENROUTER_API_KEY — Ваш API ключ
  MENTAL_MASTERY_MODEL — Модель (по умолчанию: claude-3.5-sonnet)[/dim]
            """,
            title="⚙️ Настройки",
            border_style="yellow"
        ))


def main():
    """Точка входа CLI."""
    app = MentalMasteryCLI()
    try:
        app.run()
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Прервано пользователем[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Ошибка: {e}[/red]")
        console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    main()
