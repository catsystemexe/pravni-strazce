# llm/client.py
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional, Literal, Any


Role = Literal["system", "user", "assistant"]


@dataclass
class LLMMessage:
    role: Role
    content: str


class LLMClient:
    """
    Jednotná brána k LLM.

    Režimy (řízené env proměnnými):

    - LLM_BACKEND=mock  (default)  -> žádné API volání, levné testy
    - LLM_BACKEND=openai         -> pokus o reálné volání OpenAI
    """

    def __init__(self) -> None:
        self.backend = os.getenv("LLM_BACKEND", "mock").lower()

        # lazy import openai – aby testy nepadaly na pydantic_core atd.
        self._openai_client = None
        if self.backend == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                # Bez klíče nemá smysl se snažit o openai režim
                self.backend = "mock"
            else:
                try:
                    from openai import OpenAI  # type: ignore

                    self._openai_client = OpenAI(api_key=api_key)
                except Exception:
                    # Když selže import nebo client, spadneme zpět do mock režimu
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
        if self.backend == "openai" and self._openai_client is not None:
            return self._chat_openai(messages, temperature, max_tokens)

        # fallback / testovací mock
        return self._chat_mock(use_case, messages)

    # --- interní implementace backendů ---

    def _chat_openai(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float],
        max_tokens: Optional[int],
    ) -> str:
        """
        Reálné volání OpenAI – snažíme se držet se nové knihovny openai.
        Ošetřené tak, aby případný pád neodstřelil celý runtime.
        """
        try:
            model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

            # převod do dict formátu, kterou openai klient očekává
            api_messages = [
                {"role": m.role, "content": m.content} for m in messages
            ]

            resp = self._openai_client.chat.completions.create(  # type: ignore[union-attr]
                model=model,
                messages=api_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            content = getattr(resp.choices[0].message, "content", None)  # type: ignore[index]
            return content or ""
        except Exception as e:
            # V produkci chceme radši degradovat na skeleton než spadnout
            return f"[LLM ERROR] {e}"

    def _chat_mock(self, use_case: str, messages: List[LLMMessage]) -> str:
        """
        Mock odpověď – bez externích nákladů.
        Rozlišuje jen use_case, aby šla v testech rozpoznat struktura.
        """
        user_text = ""
        for m in messages:
            if m.role == "user":
                user_text = m.content
                break

        if use_case == "legal_analysis":
            return (
                "Mock LLM odpověď pro právní analýzu.\n"
                f"Uživatelský dotaz: {user_text[:200]}..."
            )

        if use_case == "jurisprudence_search":
            return (
                '{"cases": [], "note": "Mock režim – judikatura nebyla opravdu hledána."}'
            )

        return f"Mock LLM odpověď (use_case={use_case})."