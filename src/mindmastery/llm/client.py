"""LLM client for OpenRouter API."""

import json
import os
from typing import Optional
from openai import OpenAI
from rich.console import Console

console = Console()


class LLMClient:
    """Client for LLM interactions via OpenRouter."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "google/gemini-2.5-pro-preview",
        base_url: str = "https://openrouter.ai/api/v1"
    ):
        self.model = model
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")

        if not self.api_key:
            raise ValueError(
                "OpenRouter API key required. Set OPENROUTER_API_KEY env var "
                "or pass api_key parameter. Get your key at https://openrouter.ai/keys"
            )

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=base_url,
            default_headers={
                "HTTP-Referer": "https://github.com/NikasAl/mindmastery",
                "X-Title": "MindMastery"
            }
        )

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> str:
        """Get completion from LLM."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            console.print(f"[red]LLM Error: {e}[/red]")
            raise

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> dict:
        """Get JSON completion from LLM."""
        response = self.complete(system_prompt, user_prompt, temperature, max_tokens)

        # Extract JSON from markdown code blocks if present
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            response = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            response = response[start:end].strip()

        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            console.print(f"[red]JSON Parse Error: {e}[/red]")
            console.print(f"[yellow]Response was:[/yellow]\n{response[:500]}...")
            raise

    def decompose_task(self, task: str, task_type: str = "math") -> dict:
        """Decompose a task into skills."""
        from .prompts import DECOMPOSITION_SYSTEM_PROMPT, get_decomposition_prompt

        user_prompt = get_decomposition_prompt(task, task_type)
        return self.complete_json(DECOMPOSITION_SYSTEM_PROMPT, user_prompt)

    def generate_exercises(self, skill: dict, context: str, skill_id: str) -> dict:
        """Generate exercises for a skill."""
        from .prompts import DECOMPOSITION_SYSTEM_PROMPT, get_exercise_prompt

        user_prompt = get_exercise_prompt(skill, context, skill_id)
        return self.complete_json(DECOMPOSITION_SYSTEM_PROMPT, user_prompt)

    def verify_answer(self, exercise: dict, answer: str) -> dict:
        """Verify an answer to an exercise."""
        from .prompts import DECOMPOSITION_SYSTEM_PROMPT, VERIFICATION_PROMPT

        user_prompt = VERIFICATION_PROMPT.format(
            exercise=json.dumps(exercise, ensure_ascii=False, indent=2),
            answer=answer
        )
        return self.complete_json(DECOMPOSITION_SYSTEM_PROMPT, user_prompt)
