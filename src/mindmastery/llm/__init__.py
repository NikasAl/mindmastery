"""LLM module for MindMastery."""

from .client import LLMClient
from .prompts import (
    DECOMPOSITION_SYSTEM_PROMPT,
    DECOMPOSITION_PROMPT,
    EXERCISE_GENERATION_PROMPT,
    VERIFICATION_PROMPT,
    get_decomposition_prompt,
    get_exercise_prompt,
)

__all__ = [
    "LLMClient",
    "DECOMPOSITION_SYSTEM_PROMPT",
    "DECOMPOSITION_PROMPT",
    "EXERCISE_GENERATION_PROMPT",
    "VERIFICATION_PROMPT",
    "get_decomposition_prompt",
    "get_exercise_prompt",
]
