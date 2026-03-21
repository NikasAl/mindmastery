"""Visualization module for rendering tasks and exercises."""

import subprocess
import webbrowser
from pathlib import Path
from typing import Optional
from datetime import datetime
from rich.console import Console

from models import TaskDecomposition, Exercise, Difficulty

console = Console()


class MarkdownRenderer:
    """Renders tasks and exercises to Markdown with LaTeX."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path.home() / ".mental_mastery" / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def render_task_decomposition(
        self,
        decomposition: TaskDecomposition,
        task_id: str
    ) -> Path:
        """Render full task decomposition to Markdown."""
        filepath = self.output_dir / f"task_{task_id}.md"

        content = self._build_decomposition_markdown(decomposition, task_id)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        console.print(f"[green]✓ Saved to: {filepath}[/green]")
        return filepath

    def _build_decomposition_markdown(
        self,
        decomposition: TaskDecomposition,
        task_id: str
    ) -> str:
        """Build Markdown content for task decomposition."""
        lines = [
            "---",
            f"title: Task {task_id}",
            f"created: {datetime.now().isoformat()}",
            "tags: [mental-mastery, task]",
            "---",
            "",
            "# 🧠 Task Decomposition",
            "",
            "## 📋 Original Task",
            "",
            f"$$ {decomposition.original_task} $$",
            "",
            "> **Plain text:**",
            "> " + decomposition.original_task_plain,
            "",
            "## 🔍 Full Solution",
            "",
        ]

        for i, step in enumerate(decomposition.full_solution, 1):
            lines.append(f"{i}. {step}")

        lines.extend([
            "",
            "---",
            "",
            "## 🎯 Required Skills",
            "",
        ])

        for skill in decomposition.skills:
            lines.extend([
                f"### {skill.name}",
                "",
                f"- **Category:** `{skill.category.value}`",
                f"- **Difficulty:** {'⭐' * skill.difficulty_base} ({skill.difficulty_base}/10)",
                f"- **Cognitive Load:** {'🧠' * skill.cognitive_load} ({skill.cognitive_load}/10)",
                "",
                f"**Description:** {skill.description}",
                "",
            ])

            if skill.prerequisites:
                lines.append(f"**Prerequisites:** {', '.join(skill.prerequisites)}")
                lines.append("")

            if skill.tips:
                lines.append("**Tips:**")
                for tip in skill.tips:
                    lines.append(f"- {tip}")
                lines.append("")

            if skill.mnemonics:
                lines.append(f"**🧩 Mnemonic:** {skill.mnemonics}")
                lines.append("")

            # Add exercises for this skill
            if skill.id in decomposition.exercises:
                lines.append("**📝 Exercises:**")
                lines.append("")
                for ex in decomposition.exercises[skill.id]:
                    lines.extend([
                        f"#### Level: {ex.level.value}",
                        "",
                        f"**Question:** $$ {ex.question} $$",
                        "",
                        f"> {ex.question_plain}",
                        "",
                        "<details>",
                        "<summary>👁️ Show Answer</summary>",
                        "",
                        f"**Answer:** `{ex.answer}`",
                        "",
                        "**Solution:**",
                        "",
                    ])
                    for step in ex.solution_steps:
                        lines.append(f"- {step}")

                    if ex.hints:
                        lines.extend([
                            "",
                            "**Hints:**",
                        ])
                        for h in ex.hints:
                            lines.append(f"- {h}")

                    lines.extend([
                        "</details>",
                        "",
                        "---",
                        "",
                    ])

        # Skill dependency graph
        lines.extend([
            "## 📊 Skill Graph",
            "",
            "```mermaid",
            "graph TD",
        ])

        for skill_id, deps in decomposition.skill_graph.items():
            if skill_id == "order":
                continue
            for dep in deps:
                lines.append(f"    {dep} --> {skill_id}")

        lines.extend([
            "```",
            "",
        ])

        return "\n".join(lines)

    def render_exercise(
        self,
        exercise: Exercise,
        show_answer: bool = False
    ) -> str:
        """Render single exercise as Markdown."""
        lines = [
            f"## Exercise [{exercise.level.value}]",
            "",
            f"**Question:** $$ {exercise.question} $$",
            "",
            f"> {exercise.question_plain}",
            "",
        ]

        if show_answer:
            lines.extend([
                "---",
                "",
                f"**Answer:** `{exercise.answer}`",
                "",
                "**Solution steps:**",
                "",
            ])
            for step in exercise.solution_steps:
                lines.append(f"- {step}")
        else:
            lines.extend([
                "---",
                "",
                "<details>",
                "<summary>👁️ Show hints</summary>",
                "",
            ])
            for i, hint in enumerate(exercise.hints, 1):
                lines.append(f"{i}. {hint}")
            lines.extend([
                "</details>",
                "",
            ])

        return "\n".join(lines)

    def render_practice_session(
        self,
        exercise: Exercise,
        skill_name: str,
        task_id: str
    ) -> Path:
        """Render a practice session file."""
        filepath = self.output_dir / f"practice_{task_id}_{exercise.id}.md"

        content = f"""---
title: Practice - {skill_name}
---

# 🎯 Practice Exercise

**Skill:** {skill_name}
**Level:** {exercise.level.value}
**Time estimate:** {exercise.time_estimate}s
**Cognitive load:** {'🧠' * exercise.cognitive_load}

---

## 📝 Question

$$ {exercise.question} $$


> {exercise.question_plain}

---

## 💭 Think about it...

*Solve this in your mind before revealing the answer.*

<details>
<summary>🔍 Need a hint?</summary>

"""
        for i, hint in enumerate(exercise.hints, 1):
            content += f"\n**Hint {i}:** {hint}\n"

        content += f"""
</details>

---

<details>
<summary>✅ Check Answer</summary>

**Correct answer:** `{exercise.answer}`

**Solution:**
"""
        for step in exercise.solution_steps:
            content += f"\n- {step}"

        content += """
</details>

---

*Practice makes perfect! 🌟*
"""

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return filepath

    def open_in_obsidian(self, filepath: Path):
        """Try to open file in Obsidian."""
        # Try to open with Obsidian
        try:
            # Check if obsidian command exists
            result = subprocess.run(
                ["which", "obsidian"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                subprocess.Popen(
                    ["obsidian", str(filepath)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                console.print("[green]✓ Opened in Obsidian[/green]")
                return
        except Exception:
            pass

        # Fallback: open in default browser (for LaTeX rendering)
        self.open_in_browser(filepath)

    def open_in_browser(self, filepath: Path):
        """Open file in browser (requires local markdown server or conversion)."""
        # Create HTML version with MathJax for browser viewing
        html_path = filepath.with_suffix(".html")
        html_content = self._markdown_to_html(filepath)

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        webbrowser.open(f"file://{html_path}")
        console.print(f"[green]✓ Opened in browser: {html_path}[/green]")

    def _markdown_to_html(self, md_path: Path) -> str:
        """Convert Markdown with LaTeX to HTML with MathJax."""
        with open(md_path, "r", encoding="utf-8") as f:
            md_content = f.read()

        # Simple conversion - in production would use proper markdown library
        import re

        # Convert markdown headers
        html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", md_content, flags=re.MULTILINE)
        html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
        html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)

        # Convert bold and italic
        html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
        html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)

        # Convert blockquotes
        html = re.sub(r"^> (.+)$", r"<blockquote>\1</blockquote>", html, flags=re.MULTILINE)

        # Convert horizontal rules
        html = re.sub(r"^---$", r"<hr>", html, flags=re.MULTILINE)

        # Keep $$ ... $$ for MathJax

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mental Mastery - Practice</title>
    <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            line-height: 1.6;
            background: #1a1a2e;
            color: #eee;
        }}
        h1, h2, h3 {{ color: #64ffda; }}
        blockquote {{
            border-left: 4px solid #64ffda;
            padding-left: 1rem;
            color: #aaa;
        }}
        code {{
            background: #16213e;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
        }}
        hr {{ border: none; border-top: 1px solid #333; margin: 2rem 0; }}
        details {{
            background: #16213e;
            padding: 1rem;
            border-radius: 8px;
            margin: 1rem 0;
        }}
        summary {{ cursor: pointer; color: #64ffda; }}
    </style>
</head>
<body>
{html}
</body>
</html>"""
