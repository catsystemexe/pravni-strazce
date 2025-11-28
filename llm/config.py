# llm/client.py
# =============================================================================
# DEPRECATED / LEGACY MODULE
#
# Tento modul (llm/config.py) je považován za **DEPRECATED**.
# Původně obsahoval alternativního LLMClienta vázaného na llm/config.yaml.
#
# Nově je jediným oficiálním LLM klientem:
#     `llm.client.LLMClient` a `llm.client.LLMMessage`
#
# Všechny nové enginy a kód by měly používat `llm.client`.
# Tento modul je zde pouze z historických důvodů a může být v budoucnu odstraněn.
# =============================================================================

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from runtime.config_loader import load_yaml

# POZOR: přizpůsob si podle používané knihovny
from openai import OpenAI  # nebo jiný oficiální klient


_CONFIG = load_yaml("llm/config.yaml")


@dataclass
class LLMMessage:
    role: str
    content: str


class LLMClient:
    """
    Tenhle klient je jediný, kdo v projektu mluví na LLM API.
    Všechny enginy by měly používat jeho.
    """

    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("Chybí OPENAI_API_KEY v environmentu.")
        self.client = OpenAI(api_key=api_key)

    def _get_params(self, use_case: str) -> Dict[str, Any]:
        if use_case == "legal_analysis":
            model = _CONFIG["model_defaults"]["legal_analysis_model"]
            temperature = _CONFIG["temperature"]["legal_analysis"]
            max_tokens = _CONFIG["max_tokens"]["legal_analysis"]
        else:
            model = _CONFIG["model_defaults"]["helper_model"]
            temperature = _CONFIG["temperature"]["helper"]
            max_tokens = _CONFIG["max_tokens"]["helper"]

        return {
            "model": model,
            "temperature": float(temperature),
            "max_tokens": int(max_tokens),
        }

    def chat(self, use_case: str, messages: List[LLMMessage]) -> str:
        """
        Obecné volání LLM.
        Vrací čistý text (obsah assistant message).
        """
        params = self._get_params(use_case)

        # přemapování na formát pro API
        api_messages = [{"role": m.role, "content": m.content} for m in messages]

        resp = self.client.chat.completions.create(
            messages=api_messages,
            **params,
        )
        return resp.choices[0].message.content.strip()
