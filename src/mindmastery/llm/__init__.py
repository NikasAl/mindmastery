"""LLM module for MindMastery."""

from .client import LLMClient, select_model, AVAILABLE_MODELS, DEFAULT_MODEL
from .prompts import (
    DECOMPOSITION_SYSTEM_PROMPT,
    DECOMPOSITION_PROMPT,
    EXERCISE_GENERATION_PROMPT,
    VERIFICATION_PROMPT,
    EXERCISE_VERIFICATION_PROMPT,
    get_decomposition_prompt,
    get_exercise_prompt,
)

__all__ = [
    "LLMClient",
    "select_model",
    "AVAILABLE_MODELS",
    "DEFAULT_MODEL",
    "DECOMPOSITION_SYSTEM_PROMPT",
    "DECOMPOSITION_PROMPT",
    "EXERCISE_GENERATION_PROMPT",
    "VERIFICATION_PROMPT",
    "EXERCISE_VERIFICATION_PROMPT",
    "get_decomposition_prompt",
    "get_exercise_prompt",
]
