# engines/questions/engine.py
from __future__ import annotations

from typing import Any, Dict, List, Optional

from engines.shared_types import EngineInput, EngineOutput
from engines.intent.loader import load_intents, IntentDefinition


def _lower(s: str | None) -> str:
    return (s or "").lower()


def _find_intent(intent_id: str) -> Optional[IntentDefinition]:
    """
    Najdi IntentDefinition podle intent_id z data/intents/*.json.
    """
    for intent_def in load_intents():
        if intent_def.intent_id == intent_id:
            return intent_def
    return None


def _select_core_questions(intent_def: IntentDefinition, max_count: int = 7) -> List[str]:
    """
    Vezme basic_questions z intentu a případně je omezí na max_count.
    """
    questions = list(intent_def.basic_questions or [])
    if max_count and len(questions) > max_count:
        questions = questions[:max_count]
    return questions


def _select_safety_questions(
    intent_def: IntentDefinition,
    risk_level: str,
    max_count: int = 5,
) -> List[str]:
    """
    Výběr bezpečnostních otázek podle risk_level.

    - high  -> všechny safety_questions (omezené max_countem)
    - medium -> první 2–3 důležité
    - low  -> klidně žádné / jen 1–2
    """
    all_safety = list(intent_def.safety_questions or [])
    if not all_safety:
        return []

    if risk_level == "high":
        qs = all_safety
    elif risk_level == "medium":
        qs = all_safety[: min(3, len(all_safety))]
    else:  # low
        qs = all_safety[: min(2, len(all_safety))]

    if max_count and len(qs) > max_count:
        qs = qs[:max_count]

    return qs


def run(engine_input: EngineInput) -> EngineOutput:
    """
    Questions Engine:

    Vstup (přes context):
      - context["case"]["user_query"] : text dotazu (pro info/debug)
      - context["intent_engine"] : payload z Intent Engine
          { "intent": "...", "domain": "...", ... }
      - context["risk_engine"]   : payload z Risk Engine
          { "risk_level": "...", "intent_id": "...", ... }

    Výstup:
      payload = {
        "intent": str,
        "domain": str,
        "risk_level": str,
        "core_questions": [..],
        "safety_questions": [..],
        "all_questions": [..],
      }
    """
    ctx = engine_input.context or {}
    case = ctx.get("case", {}) or {}
    user_query = _lower(case.get("user_query", ""))

    intent_ctx = ctx.get("intent_engine", {}) or {}
    risk_ctx = ctx.get("risk_engine", {}) or {}

    # --- 1) určení intent_id a risk_level ---
    intent_id = intent_ctx.get("intent") or risk_ctx.get("intent_id")
    risk_level = risk_ctx.get("risk_level", "low")

    if not intent_id:
        # Nemáme žádný intent -> neumíme vygenerovat otázky specifické pro situaci
        payload: Dict[str, Any] = {
            "intent": None,
            "domain": "unknown",
            "risk_level": "low",
            "core_questions": [],
            "safety_questions": [],
            "all_questions": [],
        }
        return EngineOutput(
            name="questions_engine",
            payload=payload,
            notes=["questions_engine: no intent available in context"],
        )

    intent_def = _find_intent(intent_id)
    if not intent_def:
        payload = {
            "intent": intent_id,
            "domain": "unknown",
            "risk_level": risk_level,
            "core_questions": [],
            "safety_questions": [],
            "all_questions": [],
        }
        return EngineOutput(
            name="questions_engine",
            payload=payload,
            notes=[f"questions_engine: unknown intent_id={intent_id}"],
        )

    # --- 2) core + safety questions ---
    core_questions = _select_core_questions(intent_def)
    safety_questions = _select_safety_questions(intent_def, risk_level=risk_level)

    # all_questions = nejprve core, pak safety, bez duplicit
    all_questions: List[str] = []
    for q in core_questions + safety_questions:
        if q not in all_questions:
            all_questions.append(q)

    payload: Dict[str, Any] = {
        "intent": intent_id,
        "domain": intent_def.domain,
        "risk_level": risk_level,
        "core_questions": core_questions,
        "safety_questions": safety_questions,
        "all_questions": all_questions,
    }

    notes: List[str] = [
        f"questions_engine: intent={intent_id}, domain={intent_def.domain}, "
        f"risk={risk_level}, core={len(core_questions)}, safety={len(safety_questions)}"
    ]

    return EngineOutput(
        name="questions_engine",
        payload=payload,
        notes=notes,
    )