# engines/risk/engine.py
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from engines.shared_types import EngineInput, EngineOutput
from engines.intent.loader import load_intents, IntentDefinition


def _lower(s: str | None) -> str:
    return (s or "").lower()


def _find_intent(intent_id: str) -> Optional[IntentDefinition]:
    for intent_def in load_intents():
        if intent_def.intent_id == intent_id:
            return intent_def
    return None


def _score_risks(text: str, intent_def: IntentDefinition) -> Dict[str, Any]:
    """
    Vrací:
      {
        "matches": [ {pattern, dimensions} ],
        "dimensions_count": {dimension: count}
      }
    """
    matches = []
    dims: Dict[str, int] = {}

    for rp in intent_def.risk_patterns:
        try:
            if re.search(rp.pattern, text):
                matches.append({"pattern": rp.pattern, "dimensions": rp.dimensions})
                for d in rp.dimensions:
                    dims[d] = dims.get(d, 0) + 1
        except re.error:
            # Chybný regex nesmí engine shodit
            continue

    return {
        "matches": matches,
        "dimensions_count": dims,
    }


def _resolve_risk_level(dimensions_count: Dict[str, int]) -> str:
    """
    Jednoduchá logika:
      - pokud jakákoliv dimenze >= 2 → HIGH
      - pokud existuje alespoň 1 → MEDIUM
      - jinak LOW
    """
    if not dimensions_count:
        return "low"

    # pokud některá dimenze je „zásadní“ vícekrát
    if any(v >= 2 for v in dimensions_count.values()):
        return "high"

    return "medium"


def run(engine_input: EngineInput) -> EngineOutput:
    """
    Risk Engine:
    - najde odpovídající intent (musí ho dodat Intent Engine v contextu)
    - vyhodnotí risk podle regexů
    - navrhne bezpečnostní otázky
    """
    ctx = engine_input.context or {}
    case = ctx.get("case", {}) or {}
    user_query = _lower(case.get("user_query", ""))

    # Intent Engine musí do context["intent_engine"] vložit {"intent": "..."}
    intent_data = ctx.get("intent_engine", {})
    intent_id = intent_data.get("intent")

    if not intent_id:
        return EngineOutput(
            name="risk_engine",
            payload={"risk_level": "low", "matches": [], "dimensions": {}},
            notes=["risk_engine: no intent provided"],
        )

    intent_def = _find_intent(intent_id)
    if not intent_def:
        return EngineOutput(
            name="risk_engine",
            payload={"risk_level": "low", "matches": [], "dimensions": {}},
            notes=[f"risk_engine: unknown intent_id={intent_id}"],
        )

    # --- hlavní risk scoring ---
    scoring = _score_risks(user_query, intent_def)
    risk_level = _resolve_risk_level(scoring["dimensions_count"])

    payload: Dict[str, Any] = {
        "risk_level": risk_level,
        "matches": scoring["matches"],
        "dimensions": scoring["dimensions_count"],
        "safety_questions": intent_def.safety_questions,
        "intent_id": intent_id,
    }

    return EngineOutput(
        name="risk_engine",
        payload=payload,
        notes=[f"risk_engine: risk={risk_level}, intent={intent_id}"],
    )