#!/usr/bin/env python3
"""
Demo mode for Mental Mastery - runs without LLM API key.
Uses pre-defined decompositions to demonstrate the system.
"""

import json
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm

console = Console()


# Pre-defined decompositions for demo
DEMO_DECOMPOSITIONS = {
    "fraction": {
        "original_task": r"\frac{(7 - 6,35) : 6,5 + 9,9}{\left(1,2 : 36 + 1,2 : 0,25 - 1\frac{5}{16}\right) : \frac{169}{24}}",
        "original_task_plain": "(7 - 6.35) : 6.5 + 9.9 / (1.2 : 36 + 1.2 : 0.25 - 1 5/16) : 169/24",
        "full_solution": [
            "Вычисляем числитель:",
            "  7 - 6.35 = 0.65 (вычитание десятичных)",
            "  0.65 : 6.5 = 0.1 (деление на число в 10 раз больше)",
            "  0.1 + 9.9 = 10 (сложение)",
            "Вычисляем знаменатель:",
            "  1.2 : 36 = 1/30 (деление на 36)",
            "  1.2 : 0.25 = 4.8 (деление на 0.25 = умножение на 4)",
            "  1 5/16 = 21/16 (перевод смешанного числа)",
            "  1/30 + 4.8 - 21/16 = 4.8 - 21/16 + 1/30",
            "  = 4.8 - 1.3125 + 0.033... = 3.5208...",
            "  Или: 24/5 - 21/16 + 1/30 = приводим к общему знаменателю 240",
            "  = 1152/240 - 315/240 + 8/240 = 845/240 = 169/48",
            "  169/48 : 169/24 = 169/48 * 24/169 = 1/2",
            "Итоговый ответ: 10 : 0.5 = 20"
        ],
        "skills": [
            {
                "id": "dec_subtract",
                "name": "Вычитание десятичных дробей",
                "description": "Умение вычитать десятичные дроби с разным числом знаков после запятой. Ключевой навык: выравнивание разрядов.",
                "category": "COMPUTATIONAL",
                "difficulty_base": 2,
                "cognitive_load": 2,
                "prerequisites": [],
                "tips": [
                    "Представь числа столбиком",
                    "Допиши нули для выравнивания: 7.00 - 6.35",
                    "Проверь: 6.35 + 0.65 = 7.00"
                ],
                "mnemonics": "Для 7 - 6.35: думай 'сколько добавить до 7?' → 0.65"
            },
            {
                "id": "pattern_div_10x",
                "name": "Паттерн: деление на число ×10",
                "description": "Деление на число, которое в 10 раз больше делимого. Паттерн: a : 10a = 0.1",
                "category": "COMPUTATIONAL",
                "difficulty_base": 3,
                "cognitive_load": 2,
                "prerequisites": ["dec_subtract"],
                "tips": [
                    "0.65 : 6.5 — заметь что 65 : 650 = 0.1",
                    "Общий паттерн: x : 10x = 0.1"
                ],
                "mnemonics": "Число на число в 10 раз больше = одна десятая"
            },
            {
                "id": "pattern_div_025",
                "name": "Паттерн: деление на 0.25",
                "description": "Деление на 0.25 эквивалентно умножению на 4. Полезный паттерн для устного счёта.",
                "category": "COMPUTATIONAL",
                "difficulty_base": 3,
                "cognitive_load": 2,
                "prerequisites": [],
                "tips": [
                    "0.25 = 1/4, поэтому a : 0.25 = a × 4",
                    "1.2 : 0.25 = 1.2 × 4 = 4.8"
                ],
                "mnemonics": "Делить на четверть = умножить на 4"
            },
            {
                "id": "mixed_to_fraction",
                "name": "Перевод смешанного числа",
                "description": "Перевод смешанного числа (1 5/16) в неправильную дробь (21/16).",
                "category": "COMPUTATIONAL",
                "difficulty_base": 3,
                "cognitive_load": 3,
                "prerequisites": [],
                "tips": [
                    "1 × 16 + 5 = 21, знаменатель остаётся 16",
                    "Паттерн: a b/c = (a×c + b)/c"
                ],
                "mnemonics": "Целая часть × знаменатель + числитель"
            },
            {
                "id": "frac_common_denom",
                "name": "Приведение к общему знаменателю",
                "description": "Нахождение НОК знаменателей и приведение дробей. В задаче: 30, 16 → НОК = 240.",
                "category": "COMPUTATIONAL",
                "difficulty_base": 5,
                "cognitive_load": 4,
                "prerequisites": ["mixed_to_fraction"],
                "tips": [
                    "НОК(30, 16) = 240",
                    "1/30 = 8/240, 21/16 = 315/240",
                    "4.8 = 24/5 = 1152/240"
                ],
                "mnemonics": "Разложи на простые множители: 30=2×3×5, 16=2⁴ → НОК=2⁴×3×5=240"
            },
            {
                "id": "working_memory_3",
                "name": "Рабочая память: 3 слота",
                "description": "Удержание 3 промежуточных результатов в уме одновременно.",
                "category": "MEMORY",
                "difficulty_base": 4,
                "cognitive_load": 5,
                "prerequisites": [],
                "tips": [
                    "Используй chunking: группируй связанные числа",
                    "Повторяй промежуточные результаты про себя",
                    "Визуализируй числа как образы"
                ],
                "mnemonics": "Метод локусов: представь 3 числа в 3 местах комнаты"
            },
            {
                "id": "frac_div_inverse",
                "name": "Деление дробей через обратную",
                "description": "a/b : c/d = a/b × d/c. Замена деления на умножение.",
                "category": "COMPUTATIONAL",
                "difficulty_base": 3,
                "cognitive_load": 3,
                "prerequisites": [],
                "tips": [
                    "169/48 : 169/24 = 169/48 × 24/169",
                    "Сократи 169 и 48, 24",
                    "= 24/48 = 1/2"
                ],
                "mnemonics": "Переверни вторую и умножь"
            },
            {
                "id": "final_assembly",
                "name": "Финальная сборка",
                "description": "Соединение всех частей выражения для получения ответа.",
                "category": "STRATEGIC",
                "difficulty_base": 5,
                "cognitive_load": 6,
                "prerequisites": ["working_memory_3", "frac_div_inverse"],
                "tips": [
                    "Числитель = 10",
                    "Знаменатель = 1/2",
                    "10 : 1/2 = 10 × 2 = 20"
                ],
                "mnemonics": "Собери всё как пазл"
            }
        ],
        "skill_graph": {
            "order": ["dec_subtract", "pattern_div_10x", "pattern_div_025", "mixed_to_fraction", "frac_common_denom", "working_memory_3", "frac_div_inverse", "final_assembly"],
            "dec_subtract": [],
            "pattern_div_10x": ["dec_subtract"],
            "pattern_div_025": [],
            "mixed_to_fraction": [],
            "frac_common_denom": ["mixed_to_fraction"],
            "working_memory_3": [],
            "frac_div_inverse": [],
            "final_assembly": ["working_memory_3", "frac_div_inverse"]
        }
    },
    "word_problem": {
        "original_task": "Половина — треть некоторого числа. Какое это число?",
        "original_task_plain": "Половина — треть некоторого числа. Какое это число?",
        "full_solution": [
            "Понимание условия: 1/2 = 1/3 × x",
            "где x — искомое число",
            "Переводим в уравнение: 1/2 = x/3",
            "Решаем: x = 3 × 1/2 = 3/2 = 1.5",
            "Проверка: 1/3 от 1.5 = 0.5 = 1/2 ✓"
        ],
        "skills": [
            {
                "id": "text_to_equation",
                "name": "Перевод текста в уравнение",
                "description": "Умение преобразовать словесное условие в математическую запись.",
                "category": "STRATEGIC",
                "difficulty_base": 4,
                "cognitive_load": 4,
                "prerequisites": [],
                "tips": [
                    "'Половина' = 1/2",
                    "'Треть числа' = число/3",
                    "'—' означает равенство"
                ],
                "mnemonics": "Ключевые слова → математические символы"
            },
            {
                "id": "mental_canvas",
                "name": "Мысленный холст",
                "description": "Визуализация условия задачи в уме без записи на бумаге.",
                "category": "VISUALIZATION",
                "difficulty_base": 4,
                "cognitive_load": 5,
                "prerequisites": [],
                "tips": [
                    "Представь уравнение как образ: 1/2 = x/3",
                    "Визуализируй баланс весов"
                ],
                "mnemonics": "Рисуй в воображении как на доске"
            },
            {
                "id": "simple_frac_equation",
                "name": "Решение простого дробного уравнения",
                "description": "Нахождение x из уравнения a = x/b.",
                "category": "COMPUTATIONAL",
                "difficulty_base": 3,
                "cognitive_load": 3,
                "prerequisites": ["text_to_equation"],
                "tips": [
                    "x = a × b",
                    "x = 1/2 × 3 = 3/2"
                ],
                "mnemonics": "Умножь обе части на знаменатель"
            },
            {
                "id": "verification",
                "name": "Проверка ответа",
                "description": "Подстановка найденного ответа для проверки.",
                "category": "STRATEGIC",
                "difficulty_base": 2,
                "cognitive_load": 2,
                "prerequisites": ["simple_frac_equation"],
                "tips": [
                    "1/3 от 1.5 = ?",
                    "1.5 ÷ 3 = 0.5 = 1/2 ✓"
                ],
                "mnemonics": "Всегда проверяй обратным действием"
            }
        ],
        "skill_graph": {
            "order": ["text_to_equation", "mental_canvas", "simple_frac_equation", "verification"],
            "text_to_equation": [],
            "mental_canvas": [],
            "simple_frac_equation": ["text_to_equation"],
            "verification": ["simple_frac_equation"]
        }
    }
}


def generate_demo_exercises(skill_id: str) -> list:
    """Generate demo exercises for a skill."""

    exercise_templates = {
        "dec_subtract": [
            {"level": "intro", "question": "1.5 - 0.5", "answer": "1", "question_plain": "1.5 - 0.5"},
            {"level": "intro", "question": "3.0 - 1.2", "answer": "1.8", "question_plain": "3.0 - 1.2"},
            {"level": "basic", "question": "5 - 2.35", "answer": "2.65", "question_plain": "5 - 2.35"},
            {"level": "basic", "question": "10 - 3.75", "answer": "6.25", "question_plain": "10 - 3.75"},
            {"level": "intermediate", "question": "7 - 6.35", "answer": "0.65", "question_plain": "7 - 6.35"},
        ],
        "pattern_div_10x": [
            {"level": "intro", "question": "5 : 50", "answer": "0.1", "question_plain": "5 : 50"},
            {"level": "basic", "question": "0.3 : 3", "answer": "0.1", "question_plain": "0.3 : 3"},
            {"level": "intermediate", "question": "0.65 : 6.5", "answer": "0.1", "question_plain": "0.65 : 6.5"},
        ],
        "pattern_div_025": [
            {"level": "intro", "question": "1 : 0.25", "answer": "4", "question_plain": "1 : 0.25"},
            {"level": "basic", "question": "2 : 0.25", "answer": "8", "question_plain": "2 : 0.25"},
            {"level": "intermediate", "question": "1.2 : 0.25", "answer": "4.8", "question_plain": "1.2 : 0.25"},
        ],
        "text_to_equation": [
            {"level": "intro", "question": "'Удвоенное число равно 10' → ?", "answer": "2x = 10", "question_plain": "Удвоенное число равно 10. Запиши уравнение."},
            {"level": "basic", "question": "'Половина числа равна 5' → ?", "answer": "x/2 = 5", "question_plain": "Половина числа равна 5. Запиши уравнение."},
            {"level": "intermediate", "question": "'Треть числа равна половине' → ?", "answer": "x/3 = 1/2", "question_plain": "Треть числа равна половине. Запиши уравнение."},
        ],
    }

    return exercise_templates.get(skill_id, [
        {"level": "intro", "question": f"Упражнение для {skill_id}", "answer": "ответ", "question_plain": f"Базовое упражнение для навыка {skill_id}"}
    ])


def run_demo():
    """Run demo mode."""
    console.clear()
    console.print(Panel(
        """
[bold cyan]🧠 Mental Mastery - Demo Mode[/bold cyan]

This demo runs without an API key, using pre-defined decompositions.

Available example tasks:
• Fraction expression (Сканави)
• Word problem (Половина — треть)

[italic]Demo mode shows the workflow and UI.[/italic]
        """,
        border_style="cyan",
        padding=(1, 2)
    ))

    while True:
        console.print("\n[bold]Select example:[/bold]")
        console.print("  1. Fraction expression (Сканави)")
        console.print("  2. Word problem")
        console.print("  q. Quit")

        choice = Prompt.ask("\nChoice", choices=["1", "2", "q"], default="1")

        if choice == "q":
            console.print("\n[cyan]Thanks for trying Mental Mastery! 🧠[/cyan]\n")
            break

        demo_key = "fraction" if choice == "1" else "word_problem"
        demo_data = DEMO_DECOMPOSITIONS[demo_key]

        # Show decomposition
        console.print(Panel(
            f"$$ {demo_data['original_task']} $$\n\n[dim]{demo_data['original_task_plain']}[/dim]",
            title="📋 Task",
            border_style="cyan"
        ))

        # Show solution
        console.print("\n[bold]📝 Full Solution:[/bold]")
        for i, step in enumerate(demo_data["full_solution"], 1):
            console.print(f"  {i}. {step}")

        # Show skills table
        table = Table(title=f"\n🎯 Identified Skills ({len(demo_data['skills'])} total)")
        table.add_column("#", width=3)
        table.add_column("Skill", style="green")
        table.add_column("Category", style="cyan")
        table.add_column("Diff", style="yellow")
        table.add_column("Load", style="magenta")

        for i, skill in enumerate(demo_data["skills"], 1):
            table.add_row(
                str(i),
                skill["name"],
                skill["category"],
                "⭐" * skill["difficulty_base"],
                "🧠" * skill["cognitive_load"]
            )

        console.print(table)

        # Offer to practice
        if Confirm.ask("\nPractice a skill?", default=True):
            console.print("\n[bold]Select skill to practice:[/bold]")
            for i, skill in enumerate(demo_data["skills"], 1):
                console.print(f"  {i}. {skill['name']}")

            skill_choice = Prompt.ask("Select", default="1")
            try:
                skill_idx = int(skill_choice) - 1
                if 0 <= skill_idx < len(demo_data["skills"]):
                    skill = demo_data["skills"][skill_idx]
                    practice_skill_demo(skill)
            except ValueError:
                console.print("[red]Invalid selection[/red]")


def practice_skill_demo(skill: dict):
    """Practice a skill in demo mode."""
    console.print(f"\n[bold cyan]🎯 {skill['name']}[/bold cyan]")
    console.print(f"[dim]{skill['description']}[/dim]")

    if skill.get("tips"):
        console.print("\n[bold]💡 Tips:[/bold]")
        for tip in skill["tips"]:
            console.print(f"  • {tip}")

    if skill.get("mnemonics"):
        console.print(f"\n[bold]🧩 Mnemonic:[/bold] {skill['mnemonics']}")

    # Get exercises
    exercises = generate_demo_exercises(skill["id"])

    console.print(f"\n[bold]📝 Exercises:[/bold]")

    for i, ex in enumerate(exercises, 1):
        console.print(f"\n[bold]{i}. [{ex['level']}] {ex['question_plain']}[/bold]")

        user_answer = Prompt.ask("Your answer (or 's' to skip)")

        if user_answer.lower() == 's':
            console.print(f"[yellow]Answer: {ex['answer']}[/yellow]")
        elif user_answer.strip().lower() == ex['answer'].lower():
            console.print("[green]✓ Correct![/green]")
        else:
            console.print(f"[red]✗ Incorrect. Correct answer: {ex['answer']}[/red]")

    console.print("\n[green]Skill practice complete![/green]")


if __name__ == "__main__":
    run_demo()
