"""
Judikatura Engine – v1.3

Režimy:
- DEFAULT (bez use_llm a bez env proměnných):
    → čistý skeleton + debug_candidates
    → kompatibilní s testy, žádné volání LLM

- LLM režim:
    → aktivuje se, pokud:
        * context["use_llm"] == True
        NEBO
        * PRAVNI_STRAZCE_LLM_JUDIKATURA=1
        NEBO
        * PIPELINE_USE_LLM je "1"/"true"/"yes"
    → pokusí se přes LLM navrhnout relevantní judikaturu

Testy:
- používají debug_candidates → ta mají vždy přednost
- pro "none_found" test je LLM režim vypnutý → status = NONE_FOUND
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

from engines.shared_types import EngineInput, EngineOutput

# LLM klient je volitelný – nechceme, aby jeho absence rozbíjela testy
try:
    from llm.client import LLMClient, LLMMessage  # type: ignore
except Exception:  # pragma: no cover - čistě obranný kód
    LLMClient = None  # type: ignore[assignment]
    LLMMessage = None  # type: ignore[assignment]

# Prompt soubor pro judikaturu
PROMPT_PATH = Path(__file__).parent / "prompts" / "judikatura_lookup.md"


# --------------------------------------------------------------------
# Pomocné funkce – LLM / prompty
# --------------------------------------------------------------------


def _load_prompt() -> str:
    """
    Načte prompt pro vyhledávání judikatury.
    Pokud soubor chybí, vrátí nouzovou verzi.
    """
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        return """
Jsi právní asistent zaměřený na českou judikaturu (NS, ÚS, NSS, krajské soudy).
Na základě dotazu uživatele navrhni několik (1–5) nejrelevantnějších rozhodnutí.

Výstup:
- Odpovídej výhradně jako JSON objekt se strukturou:
  {
    "cases": [
      {
        "id": "string",
        "court_level": "ns|us|nss|ks|os|ms|jiny",
        "reference": "spisová značka",
        "year": 2020,
        "legal_issue": "stručný popis právní otázky",
        "holding_summary": "jednověté shrnutí rozhodnutí",
        "holding_direction": "pro_appellant|pro_defendant|neutral|mixed",
        "relevance_score": 0.0,
        "source": "např. NS ČR / NALUS / Sbírka NS"
      }
    ]
  }

- Nepřidávej žádný komentář mimo JSON.
/NO_HALLUCINATIONS
/STRUCTURED_OUTPUT
/ABSTRACT_ONLY
        """.strip()


def _llm_enabled(ctx: Optional[Dict[str, Any]] = None) -> bool:
    """
    Rozhodne, zda je LLM režim aktivní.

    Priority:
    - context["use_llm"] (např. z orchestratoru / demo CLI)
    - env PRAVNI_STRAZCE_LLM_JUDIKATURA=1
    - env PIPELINE_USE_LLM in ("1","true","yes")
    """
    ctx = ctx or {}
    ctx_flag = bool(ctx.get("use_llm"))

    env_flag = os.getenv("PRAVNI_STRAZCE_LLM_JUDIKATURA") == "1"
    pipeline_flag = os.getenv("PIPELINE_USE_LLM", "").lower() in ("1", "true", "yes")

    return ctx_flag or env_flag or pipeline_flag


def _try_llm_candidates(case: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Zkusí přes LLM vygenerovat seznam kandidátních judikátů.

    Vrací (candidates, error_message). Pokud se cokoliv pokazí, candidates=[]
    a error_message obsahuje text chyby.
    """
    if LLMClient is None or LLMMessage is None:
        return [], "LLMClient není k dispozici (není nainstalován nebo import selhal)."

    user_query = case.get("user_query", "")
    domain = case.get("domain", "")

    base_prompt = _load_prompt()

    # System prompt – policy + role
    system_prompt = base_prompt

    # User prompt – konkrétní případ
    user_content = (
        f"Právní doména: {domain or 'neuvedeno'}\n\n"
        f"Popis situace:\n\"\"\"{user_query}\"\"\""
    )

    messages = [
        LLMMessage(role="system", content=system_prompt),
        LLMMessage(role="user", content=user_content),
    ]

    try:
        client = LLMClient()
    except Exception as e:  # pragma: no cover
        return [], f"Chyba při vytváření LLMClient: {e}"

    try:
        # Pozn.: signatura client.chat může být v tvém projektu rozšířená;
        # pokud máš use_case/temperature/max_tokens, můžeš je sem doplnit.
        result = client.chat(messages)  # type: ignore[arg-type]
    except Exception as e:  # pragma: no cover
        return [], f"Chyba při volání LLM: {e}"

    # Očekáváme, že client.chat vrátí string nebo objekt s .content
    if isinstance(result, str):
        content = result
    else:
        content = getattr(result, "content", None) or str(result)

    try:
        data = json.loads(content)
    except Exception as e:  # pragma: no cover
        return [], f"Chyba při parsování JSON z LLM: {e}"

    cases = data.get("cases") or data.get("matches") or []
    if not isinstance(cases, list):
        return [], "LLM odpověď neobsahuje pole 'cases' jako seznam."

    # lehké očištění – zajistí, že každý prvek je dict
    cleaned: List[Dict[str, Any]] = [c for c in cases if isinstance(c, dict)]
    return cleaned, None


# --------------------------------------------------------------------
# Hlavní vstupní bod
# --------------------------------------------------------------------


def run(engine_input: EngineInput) -> EngineOutput:
    ctx = engine_input.context or {}
    case = ctx.get("case", {}) or {}

    # 1) Priorita: debug_candidates (testovací režim)
    debug_candidates: List[Dict[str, Any]] = ctx.get("debug_candidates", []) or []

    llm_error: Optional[str] = None

    if debug_candidates:
        candidates = debug_candidates
        llm_used = False
    elif _llm_enabled(ctx):
        # 2) LLM režim – pouze pokud výslovně povolíš use_llm/env
        candidates, llm_error = _try_llm_candidates(case)
        llm_used = True
    else:
        # 3) Skeleton režim – žádné kandidáty, žádné LLM volání
        candidates = []
        llm_used = False

    # Základ payloadu – včetně conflict info
    payload: Dict[str, Any] = {
        "matches": candidates,
        "cases": candidates,
        "status": None,
        "notes": [],
        "conflict_info": {
            "conflict": False,
            "directions": [],
            "count": len(candidates),
        },
        "llm_used": llm_used,
    }

    if llm_error:
        payload["llm_error"] = llm_error

    # ----- 1) Žádní kandidáti -----
    if not candidates:
        payload["status"] = "NONE_FOUND"
        payload["notes"].append("Nebyla nalezena žádná judikatura.")
        if llm_error:
            payload["notes"].append(f"LLM error: {llm_error}")

        return EngineOutput(
            name="judikatura_engine",
            payload=payload,
            notes=["judikatura_engine: NONE_FOUND"],
        )

    # ----- 2) Konflikt v holding_direction -----
    directions = [c.get("holding_direction") for c in candidates if c.get("holding_direction")]
    unique_dirs = set(directions)

    if len(unique_dirs) > 1:
        payload["status"] = "CONFLICT"
        payload["notes"].append(f"Detekován konflikt judikatury: {unique_dirs}")
        payload["conflict_info"] = {
            "conflict": True,
            "directions": list(unique_dirs),
            "count": len(candidates),
        }

        return EngineOutput(
            name="judikatura_engine",
            payload=payload,
            notes=["judikatura_engine: CONFLICT"],
        )

    # ----- 3) Jinak OK -----
    payload["status"] = "OK"
    payload["notes"].append("Judikatura je konzistentní (bez konfliktu).")
    payload["conflict_info"] = {
        "conflict": False,
        "directions": list(unique_dirs),
        "count": len(candidates),
    }

    return EngineOutput(
        name="judikatura_engine",
        payload=payload,
        notes=["judikatura_engine: OK"],
    )