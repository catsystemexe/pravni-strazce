from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List

from runtime.config_loader import load_yaml

# ------------------------------------------------------------------
# Bezpečný import OpenAI klienta
# ------------------------------------------------------------------
# Replit/Nix + různé verze Pythonu můžou způsobit chyby typu
# ModuleNotFoundError: pydantic_core._pydantic_core
# Proto import obalíme try/except a samotný LLMClient odmávne,
# pokud klient reálně není k dispozici.
# ------------------------------------------------------------------

try:
    from openai import OpenAI  # oficiální klient
    _openai_import_exception: Exception | None = None
except Exception as e:  # schválně široké – kvůli pydantic_core chybám
    OpenAI = None  # type: ignore[assignment]
    _openai_import_exception = e

_CONFIG = load_yaml("llm/config.yaml")


@dataclass
class LLMMessage:
    role: str
    content: str


class LLMClient:
    """
    Jediný klient, který v projektu mluví na LLM API.

    Důležité:
    - samotný import modulu llm.client NESMÍ spadnout (kvůli testům),
    - pokud ale OpenAI není k dispozici nebo chybí API klíč,
      __init__ zvedne RuntimeError.
    """

    def __init__(self) -> None:
        if OpenAI is None:
            # Tohle je ok v testech – LLM se prostě nebude používat.
            raise RuntimeError(f"OpenAI klient není k dispozici: {_openai_import_exception}")

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
        api_messages = [{"role": m.role, "content": m.content} for m in messages]

        resp = self.client.chat.completions.create(
            messages=api_messages,
            **params,
        )
        return resp.choices[0].message.content.strip()