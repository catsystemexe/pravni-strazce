from __future__ import annotations

from typing import Any, Dict, List, Optional

from engines.shared_types import EngineInput, EngineOutput
from .loader import load_intents, IntentDefinition
from llm.client import LLMClient, LLMMessage


def _lower(s: str | None) -> str:
    return (s or "").lower()


# -----------------------------
# 1) Cache intent definic
# -----------------------------

_INTENTS_CACHE: Optional[List[IntentDefinition]] = None


def get_intent_definitions() -> List[IntentDefinition]:
    """
    Načte a cacheuje definice intentů z data/intents/*.json.
    """
    global _INTENTS_CACHE
    if _INTENTS_CACHE is None:
        _INTENTS_CACHE = load_intents()
    return _INTENTS_CACHE


# -----------------------------
# 2) LLM klient (volitelný doplněk)
# -----------------------------

_LLM: Optional[LLMClient] = None


def get_llm() -> LLMClient:
    """
    Lazy inicializace LLMClient – aby se nenačítal, když běžíme čistě
    v mock režimu / bez LLM.
    """
    global _LLM
    if _LLM is None:
        _LLM = LLMClient()
    return _LLM


# -----------------------------
# 3) Heuristická klasifikace
# -----------------------------

def _heuristic_classify(user_query: str) -> Dict[str, Any]:
    """
    Heuristické přiřazení intentu a domény na základě
    data/intents/*.json (IntentDefinition).

    Vrací dict:

    {
        "intent": str,
        "domain": str,
        "intent_group": str,
        "intent_scores": {id: score},
        "domain_scores": {domain: score},
        "matched_keywords": [...],
        "max_intent_score": int,
        "max_domain_score": int,
    }
    """
    text = _lower(user_query)

    intent_scores: Dict[str, int] = {}
    domain_scores: Dict[str, int] = {}
    intent_groups: Dict[str, str] = {}
    matched_keywords: List[str] = []

    for intent_def in get_intent_definitions():
        score = 0

        # bezpečný přístup – starší JSONy nemusí mít keywords / negative_keywords
        keywords = getattr(intent_def, "keywords", None) or []
        negative_keywords = getattr(intent_def, "negative_keywords", None) or []

        # pozitivní klíčová slova
        for kw in keywords:
            kw_l = kw.lower()
            if kw_l in text:
                score += 1
                if kw not in matched_keywords:
                    matched_keywords.append(kw)

        # negativní klíčová slova – penalizace, aby se intent nechytil omylem
        for neg in negative_keywords:
            if neg.lower() in text:
                score -= 2

        if score <= 0:
            continue

        intent_id = intent_def.intent_id
        domain_id = intent_def.domain

        intent_scores[intent_id] = intent_scores.get(intent_id, 0) + score
        domain_scores[domain_id] = domain_scores.get(domain_id, 0) + score

        # pokud má intent definované intent_group, uložíme si ho
        group = getattr(intent_def, "intent_group", None)
        if group:
            intent_groups[intent_id] = group

    # fallbacky
    dominant_intent = "general"
    dominant_intent_group = "info"
    dominant_domain = "unknown"
    max_intent_score = 0
    max_domain_score = 0

    for k, v in intent_scores.items():
        if v > max_intent_score:
            max_intent_score = v
            dominant_intent = k

    # odvození intent_group z nejlepšího intentu
    if dominant_intent in intent_groups:
        dominant_intent_group = intent_groups[dominant_intent]

    for k, v in domain_scores.items():
        if v > max_domain_score:
            max_domain_score = v
            dominant_domain = k

    return {
        "intent": dominant_intent,
        "domain": dominant_domain,
        "intent_group": dominant_intent_group,
        "intent_scores": intent_scores,
        "domain_scores": domain_scores,
        "matched_keywords": matched_keywords,
        "max_intent_score": max_intent_score,
        "max_domain_score": max_domain_score,
    }


# -----------------------------
# 4) Veřejný vstup enginu
# -----------------------------

def run(engine_input: EngineInput) -> EngineOutput:
    """
    Intent & Domain Engine v2 – data-driven heuristika + volitelný LLM doplněk.

    Vstup:
      context["case"]["user_query"] – text dotazu

    Výstup v payload:
      {
        "intent": "...",
        "domain": "...",
        "intent_group": "...",
        "keywords": [...],
        "confidence": float 0.0–1.0,
        "raw_intent_scores": {...},
        "raw_domain_scores": {...},
        "llm_raw": str | None,   # volitelný LLM názor
      }
    """
    ctx = engine_input.context or {}
    case = ctx.get("case", {}) or {}
    user_query = case.get("user_query", "") or ""

    # 1) heuristika nad data/intents/*
    h = _heuristic_classify(user_query)

    max_intent_score: int = h["max_intent_score"]
    max_domain_score: int = h["max_domain_score"]
    raw_intent_scores: Dict[str, int] = h["intent_scores"]
    raw_domain_scores: Dict[str, int] = h["domain_scores"]
    matched_keywords: List[str] = h["matched_keywords"]

    # hrubý odhad confidence – čím víc tref, tím vyšší
    raw_score = max(max_intent_score, max_domain_score)
    confidence = min(1.0, raw_score / 5.0) if raw_score > 0 else 0.0

    # 2) volitelný LLM doplněk – jen když je jistota nízká a backend je openai
    llm_raw: Optional[str] = None
    try:
        llm = get_llm()
        if getattr(llm, "backend", "mock") == "openai" and confidence < 0.4:
            # TODO: ideálně načíst prompt z intent_classification.md
            system_prompt = (
                "Jsi právní klasifikační modul. Na základě dotazu urči "
                "pravděpodobný právní intent a doménu. Odpovídej stručně, "
                "ideálně ve strukturovaném JSON."
            )
            messages = [
                LLMMessage(role="system", content=system_prompt),
                LLMMessage(role="user", content=user_query),
            ]
            llm_raw = llm.chat(use_case="helper", messages=messages)
    except Exception:
        # Jakýkoliv problém s LLM nesmí shodit engine – prostě LLM ignorujeme
        llm_raw = None

    payload: Dict[str, Any] = {
        "intent": h["intent"],
        "domain": h["domain"],
        "intent_group": h["intent_group"],
        "keywords": matched_keywords,
        "confidence": confidence,
        "raw_intent_scores": raw_intent_scores,
        "raw_domain_scores": raw_domain_scores,
        "llm_raw": llm_raw,
    }

    notes: List[str] = [
        f"intent_engine: intent={h['intent']}, "
        f"domain={h['domain']}, "
        f"intent_group={h['intent_group']}, "
        f"confidence={confidence}"
    ]

    return EngineOutput(
        name="intent_engine",
        payload=payload,
        notes=notes,
    )

