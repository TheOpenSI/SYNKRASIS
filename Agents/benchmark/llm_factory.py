# ====================================================================================
# Builds an LLM service from a "backend:model" spec.
# Examples:
#    - "openai:gpt-5-nano-2025-08-07"
#    - "ollama:llama3.1:8b"
# Usage:
#    - build_llm(model_spec: str, system_prompt: str, num_ctx: int = 16384) -> LLMBase
#    - safe_name(model_spec: str) -> str
# ====================================================================================

import os, sys

sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

from typing import Tuple

from services.LLM.LLMBase import LLMBase


def parse_spec(model_spec: str) -> Tuple[str, str]:
    """
    Split "backend:model" into (backend, model). Ollama model tags may contain ":" too.
    """
    backend, model_name = model_spec.split(":", 1)
    if backend not in ("openai", "ollama"):
        raise ValueError(f"Unknown backend '{backend}' in '{model_spec}', use openai: or ollama:")
    return backend, model_name


def safe_name(model_spec: str) -> str:
    """
    Folder/file friendly name for a model spec.
    """
    return model_spec.replace(":", "_").replace("/", "_")


def build_llm(model_spec: str, system_prompt: str, num_ctx: int = 16384) -> LLMBase:
    """
    Create the LLM service and set its system prompt.

    Args:
        model_spec (str): "openai:<model>" or "ollama:<model>"
        system_prompt (str): system prompt for every call
        num_ctx (int): Ollama context window, the prompts here need well over the 2-4k default
    """
    backend, model_name = parse_spec(model_spec)
    if backend == "openai":
        from services.LLM.OpenAI_GPT.OpenAI_GPT import OpenAI_GPT
        llm = OpenAI_GPT(model_name=model_name) # GPT-5 models only accept the default temperature of 1
    else:
        from services.LLM.Ollama.Ollama import Ollama # imported lazily, pulls the model on init
        llm = Ollama(model_name=model_name, options={"num_ctx": num_ctx, "seed": 42})
    llm.set_system_prompt(system_prompt)
    return llm
