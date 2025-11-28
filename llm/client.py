# llm/client.py
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Literal

from runtime.config_loader import load_yaml

# Načtení LLM konfigurace z YAML (modely, teploty, max_tokens)
_CONFIG = load_yaml("llm/config.yaml")


Role = Literal["system", "user", "assistant"]


@dataclass
class LLMMessage:
    role: Role
    content: str


def get_llm_params_for_use_case(use_case: str) -> Dict[str, Any]:
    """
    Vrací parametry pro volání LLM (model, temperature, max_tokens)
    podle use_case a konfigurace v llm/config.yaml.

    Pravidla:
      - pro `jurisprudence_search` použij helper_model + helper parametry,
      - pro ostatní use_case použij legal_analysis_model + legal_analysis parametry.
    """
    model_defaults = _CONFIG.get("model_defaults", {})
    temps = _CONFIG.get("temperature", {})
    max_tokens_cfg = _CONFIG.get("max_tokens", {})

    if use_case == "jurisprudence_search":
        model = model_defaults.get("helper_model", "gpt-4.1-mini")
        temperature = float(temps.get("helper", 0.1))
        max_tokens = int(max_tokens_cfg.get("helper", 800))
    else:
        model = model_defaults.get("legal_analysis_model", "gpt-4.1-mini")
        temperature = float(temps.get("legal_analysis", 0.2))
        max_tokens = int(max_tokens_cfg.get("legal_analysis", 2000))

    return {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }


class LLMClient:
    """
    Jednotná brána k LLM.

    backend se řídí env proměnnou LLM_BACKEND:

    - LLM_BACKEND=mock  (default)  -> žádné API volání, levné testy
    - LLM_BACKEND=openai          -> pokus o reálné volání OpenAI
    """

    def __init__(self) -> None:
        self.backend = os.getenv("LLM_BACKEND", "mock").lower()

        # lazy import openai – aby testy nepadaly, když knihovna/klíč chybí
        self._openai_client = None
        if self.backend == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                # Bez klíče nemá smysl se snažit o openai režim – degradujeme na mock
                self.backend = "mock"
            else:
                try:
                    from openai import OpenAI  # type: ignore

                    self._openai_client = OpenAI(api_key=api_key)
                except Exception:
                    # Když selže import nebo klient, spadneme zpět do mock režimu
                    self.backend = "mock"
                    self._openai_client = None

    # --- veřejné API ---

    def chat(
        self,
        use_case: str,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Hlavní vstupní bod pro všechny enginy.
        V testech bude defaultně běžet mock, v produkci se zapne přes env.
        """
        # 1) načti defaultní parametry z YAML podle use_case
        params = get_llm_params_for_use_case(use_case)

        # 2) případné přepsání explicitními argumenty
        if temperature is not None:
            params["temperature"] = float(temperature)
        if max_tokens is not None:
            params["max_tokens"] = int(max_tokens)

        # 3) rozhodnutí backendu
        if self.backend == "openai" and self._openai_client is not None:
            return self._chat_openai(messages, params)

        # fallback / testovací mock
        return self._chat_mock(use_case, messages)

    # --- interní implementace backendů ---

    def _chat_openai(
        self,
        messages: List[LLMMessage],
        params: Dict[str, Any],
    ) -> str:
        """
        Reálné volání OpenAI – snažíme se držet se nové knihovny openai.
        Ošetřené tak, aby případný pád neodstřelil celý runtime.
        """
        try:
            api_messages = [
                {"role": m.role, "content": m.content} for m in messages
            ]

            resp = self._openai_client.chat.completions.create(  # type: ignore[union-attr]
                messages=api_messages,
                **params,
            )

            content = getattr(resp.choices[0].message, "content", None)  # type: ignore[index]
            return content or ""
        except Exception as e:
            # V produkci chceme radši degradovat na skeleton než spadnout
            return f"[LLM ERROR] {e}"

    def _chat_mock(self, use_case: str, messages: List[LLMMessage]) -> str:
        """
        Jednoduchý mock pro testy a vývoj bez API klíče.
        """
        last_user_content = ""
        for m in reversed(messages):
            if m.role == "user":
                last_user_content = m.content
                break

        if use_case == "legal_analysis":
            return (
                "Mock LLM odpověď pro právní analýzu.\n\n"
                f"Poslední uživatelský vstup byl:\n{last_user_content}"
            )

        if use_case == "jurisprudence_search":
            return (
                '{"judikatura": [], "poznámka": "Mock judikatura – '
                'reálné napojení na zdroj ještě není hotové."}'
            )

        return f"Mock LLM odpověď (use_case={use_case})."
