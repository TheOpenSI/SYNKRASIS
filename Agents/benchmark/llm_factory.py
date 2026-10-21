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
from services.LLM.OpenAI_GPT.OpenAI_GPT import OpenAI_GPT
from services.LLM.Ollama.OllamaClient import OllamaClient
from services.LLM.HF_LLM.HF_LLM import HF_LLM


def parse_spec(model_spec: str) -> Tuple[str, str]:
    """
    Split "backend:model" into (backend, model). Ollama model tags may contain ":" too.

    Args:
        model_spec (str): "openai:<model>" or "ollama:<model>"
    
    Returns:
        Tuple[str, str]: (backend, model)
    """
    backend, model_name = model_spec.split(":", 1)
    if backend not in ("openai", "ollama", "hf"):
        raise ValueError(
            f"Unknown backend '{backend}' in '{model_spec}', use openai: or ollama: or hf:"
        )
    return backend, model_name


def safe_name(model_spec: str) -> str:
    """
    Folder/file friendly name for a model spec.

    Args:
        model_spec (str): "openai:<model>" or "ollama:<model>"
    
    Returns:
        str: Safe name for the model spec.
    """
    return model_spec.replace(":", "_").replace("/", "_")


def build_llm(model_spec: str,
              system_prompt: str,
              num_ctx: int = 16384) -> LLMBase:
    """
    Create the LLM service and set its system prompt.

    Args:
        model_spec (str): "openai:<model>" or "ollama:<model>" or "hf:<model>"
        system_prompt (str): system prompt for every call
        num_ctx (int): Ollama context window, the prompts here need well over the 2-4k default
    
    Returns:
        LLMBase: The LLM service instance.
    """
    backend, model_name = parse_spec(model_spec)
    if backend == "openai":
        # GPT-5 models only accept the default temperature of 1
        llm = OpenAI_GPT(model_name=model_name)

    elif backend == "hf":
        llm = HF_LLM(model_name=model_name)  # Hugging Face models

    else:
        llm = OllamaClient(
            model_name = model_name, 
            options = {"num_ctx": num_ctx, "seed": 42}
        )
        
    llm.set_system_prompt(system_prompt)
    return llm
