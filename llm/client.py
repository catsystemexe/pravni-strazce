from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List

from runtime.config_loader import load_yaml

# bezpečný import openai – jak jsme řešili dřív
try:
    from openai import OpenAI
    _openai_import_exception: Exception | None = None
except Exception as e:
    OpenAI = None  # type: ignore[assignment]
    _openai_import_exception = e

_CONFIG = load_yaml("llm/config.yaml")


@dataclass
class LLMMessage:
    role: str
    content: str


class LLMClient:
    def __init__(self) -> None:
        if OpenAI is None:
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

    def chat(
        self,
        use_case: str,
        messages: List[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """
        Obecné volání LLM.

        - use_case = "legal_analysis" / "helper"
        - pokud jsou předány temperature / max_tokens, přepíšou default
        """
        params = self._get_params(use_case)

        if temperature is not None:
            params["temperature"] = float(temperature)
        if max_tokens is not None:
            params["max_tokens"] = int(max_tokens)

        api_messages = [{"role": m.role, "content": m.content} for m in messages]

        resp = self.client.chat.completions.create(
            messages=api_messages,
            **params,
        )
        return resp.choices[0].message.content.strip()

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
