# engines/conclusion/engine.py
from __future__ import annotations

from typing import Any, Dict, List, Optional

from engines.shared_types import EngineInput, EngineOutput
from engines.intent.loader import load_intents, IntentDefinition


def _lower(s: str | None) -> str:
    return (s or "").lower()


def _normalize_risk(risk_level: str | None) -> str:
    """
    Normalizace risk_level na low/medium/high.
    Cokoliv neznámého -> low (konzervativní default).
    """
    if not risk_level:
        return "low"

    rl = _lower(risk_level)
    if rl.startswith("high"):
        return "high"
    if rl.startswith("med"):
        return "medium"
    if rl.startswith("low"):
        return "low"
    return "low"


def _find_intent(intent_id: str) -> Optional[IntentDefinition]:
    """
    Najdi IntentDefinition podle intent_id z data/intents/*.json.
    """
    for intent_def in load_intents():
        if intent_def.intent_id == intent_id:
            return intent_def
    return None


def _select_skeleton(conclusion_skeletons: Dict[str, str] | None, risk_level: str) -> Dict[str, Any]:
    """
    Vybere vhodný skeleton text pro dané risk_level.

    Pokud daný klíč chybí, zkouší fallback (např. medium -> low).
    Vrací dict:
      {
        "key": "low"|"medium"|"high",
        "text": "...",
      }
    """
    if not conclusion_skeletons:
        return {"key": None, "text": ""}

    rl = _normalize_risk(risk_level)

    # preferovaný klíč
    order: List[str]
    if rl == "high":
        order = ["high", "medium", "low"]
    elif rl == "medium":
        order = ["medium", "low", "high"]
    else:
        order = ["low", "medium", "high"]

    for key in order:
        txt = conclusion_skeletons.get(key)
        if txt:
            return {"key": key, "text": txt}

    # nic smysluplného – vrať prázdno
    return {"key": None, "text": ""}


def run(engine_input: EngineInput) -> EngineOutput:
    """
    Conclusion Engine:

    Vstup (přes context):
      - context["intent_engine"].payload:
          { "intent": "...", "domain": "...", ... }
      - context["risk_engine"].payload:
          { "risk_level": "low|medium|high", "intent_id": "...", ... }
      - context["questions_engine"].payload (volitelné):
          { "core_questions": [...], "safety_questions": [...], ... }

    Výstup:
      payload = {
        "intent": str | None,
        "domain": str | None,
        "risk_level": "low|medium|high",
        "skeleton_key": "low|medium|high" | None,
        "conclusion_text": str,
        "used_sources": {
          "intent_engine": bool,
          "risk_engine": bool,
          "questions_engine": bool,
        },
      }
    """
    ctx = engine_input.context or {}

    intent_ctx = (ctx.get("intent_engine") or {}).get("payload", {}) or {}
    risk_ctx = (ctx.get("risk_engine") or {}).get("payload", {}) or {}
    questions_ctx = (ctx.get("questions_engine") or {}).get("payload", {}) or {}

    used_sources = {
        "intent_engine": bool(intent_ctx),
        "risk_engine": bool(risk_ctx),
        "questions_engine": bool(questions_ctx),
    }

    # --- 1) intent_id + domain + risk_level ---
    # preferuj intent_id z risk_engine, fallback na intent_engine
    intent_id = risk_ctx.get("intent_id") or intent_ctx.get("intent")
    domain = intent_ctx.get("domain") or risk_ctx.get("domain") or None
    risk_level_raw = risk_ctx.get("risk_level") or "low"
    risk_level = _normalize_risk(risk_level_raw)

    if not intent_id:
        # Bez intentu nejsme schopni použít conclusion_skeletons
        payload: Dict[str, Any] = {
            "intent": None,
            "domain": domain,
            "risk_level": risk_level,
            "skeleton_key": None,
            "conclusion_text": "",
            "used_sources": used_sources,
        }
        return EngineOutput(
            name="conclusion_engine",
            payload=payload,
            notes=["conclusion_engine: no intent_id in context – skipping skeletons"],
        )

    intent_def = _find_intent(intent_id)
    if not intent_def:
        payload = {
            "intent": intent_id,
            "domain": domain,
            "risk_level": risk_level,
            "skeleton_key": None,
            "conclusion_text": "",
            "used_sources": used_sources,
        }
        return EngineOutput(
            name="conclusion_engine",
            payload=payload,
            notes=[f"conclusion_engine: intent_id={intent_id} not found in data/intents"],
        )

    # --- 2) vyber správný skeleton podle risk_level ---
    selected = _select_skeleton(intent_def.conclusion_skeletons or {}, risk_level=risk_level)
    skeleton_key = selected["key"]
    conclusion_text = selected["text"]

    # --- 3) payload ---
    payload = {
        "intent": intent_id,
        "domain": intent_def.domain or domain,
        "risk_level": risk_level,
        "skeleton_key": skeleton_key,
        "conclusion_text": conclusion_text,
        "used_sources": used_sources,
    }

    notes: List[str] = [
        f"conclusion_engine: intent={intent_id}, domain={payload['domain']}, "
        f"risk={risk_level}, skeleton={skeleton_key}",
    ]

    return EngineOutput(
        name="conclusion_engine",
        payload=payload,
        notes=notes,
    )