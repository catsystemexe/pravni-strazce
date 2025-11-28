from __future__ import annotations

from typing import Any, Dict, List

from engines.shared_types import EngineInput, EngineOutput


def _lower(s: str | None) -> str:
    return (s or "").lower()


def _score_keywords(text: str, keywords: List[str]) -> int:
    return sum(1 for kw in keywords if kw in text)


def run(engine_input: EngineInput) -> EngineOutput:
    """
    Intent & Domain Engine v1 – čistě heuristický.

    Vstup:
      context["case"]["user_query"] – text dotazu

    Výstup:
      payload = {
        "intent": "...",
        "domain": "...",
        "keywords": [...],
        "confidence": float 0.0–1.0,
      }
    """
    ctx = engine_input.context or {}
    case = ctx.get("case", {}) or {}
    user_query = _lower(case.get("user_query", ""))

    # ---------------------------
    # 1) Heuristiky pro intent
    # ---------------------------
    intent_scores: Dict[str, int] = {}

    def add_intent_score(intent: str, kws: List[str]) -> None:
        intent_scores[intent] = intent_scores.get(intent, 0) + _score_keywords(user_query, kws)

    add_intent_score("document_check", ["smlouv", "dokument", "zjistit, jestli", "zákonné", "legální"])
    add_intent_score("complaint", ["stížnost", "stiznost", "odvolán", "odvolani", "napadnout", "nesouhlasím", "nesouhlasim"])
    add_intent_score("criminal_defense", ["trestn", "policie", "pčr", "pcr", "obviněn", "obvinen", "podezření", "podezreni", "výslechu", "vyslechu"])
    add_intent_score("school_dispute", ["škola", "skola", "ředitel", "reditel", "učitel", "ucitel", "žák", "zak", "student", "ospod", "pedagog"])
    add_intent_score("inheritance", ["dědictv", "dedictv", "notář", "notar", "pozůstalost", "pozustalost"])
    add_intent_score("info", ["chci vědět", "chci vedet", "jak funguje", "jak to funguje"])

    # fallback intent – pokud nic netrefíme
    dominant_intent = "general"
    max_intent_score = 0
    for k, v in intent_scores.items():
        if v > max_intent_score:
            max_intent_score = v
            dominant_intent = k

    # ---------------------------
    # 2) Heuristiky pro domain
    # ---------------------------
    domain_scores: Dict[str, int] = {}

    def add_domain_score(domain: str, kws: List[str]) -> None:
        domain_scores[domain] = domain_scores.get(domain, 0) + _score_keywords(user_query, kws)

    # občanské / majetkové
    add_domain_score("civil", ["smlouv", "náhrada škody", "nahrada skody", "majetek", "závazek", "zavazek"])
    # trestní
    add_domain_score("criminal", ["trestn", "policie", "pčr", "pcr", "obviněn", "obvinen", "výslechu", "vyslechu"])
    # rodinné
    add_domain_score("family", ["nezletil", "dcera", "syn", "dítě", "dite", "péče", "pece", "rozvod", "výživn", "vyzivn"])
    # správní
    add_domain_score("administrative", ["úřad", "urad", "rozhodnutí", "rozhodnuti", "správní řízen", "spravni rizen"])
    # školské
    add_domain_score("school", ["škola", "skola", "učitel", "ucitel", "ředitel", "reditel", "čši", "csi", "ospod"])
    # dědické
    add_domain_score("inheritance", ["dědictv", "dedictv", "notář", "notar", "pozůstalost", "pozustalost"])

    dominant_domain = "unknown"
    max_domain_score = 0
    for k, v in domain_scores.items():
        if v > max_domain_score:
            max_domain_score = v
            dominant_domain = k

    # ---------------------------
    # 3) Confidence + keywords
    # ---------------------------
    # hrubý odhad – čím více trefených klíčových slov, tím vyšší confidence
    # (normujeme na rozsah 0.0–1.0)
    raw_score = max(max_intent_score, max_domain_score)
    confidence = min(1.0, raw_score / 5.0) if raw_score > 0 else 0.0

    # sesbíráme klíčová slova, která jsme použili (pro debug)
    matched_keywords: List[str] = []
    for intent, kws in [
        ("document_check", ["smlouv", "dokument", "zjistit, jestli", "zákonné", "legální"]),
        ("complaint", ["stížnost", "stiznost", "odvolán", "odvolani", "napadnout", "nesouhlasím", "nesouhlasim"]),
        ("criminal_defense", ["trestn", "policie", "pčr", "pcr", "obviněn", "obvinen", "podezření", "podezreni", "výslechu", "vyslechu"]),
        ("school_dispute", ["škola", "skola", "ředitel", "reditel", "učitel", "ucitel", "žák", "zak", "student", "ospod", "pedagog"]),
        ("inheritance", ["dědictv", "dedictv", "notář", "notar", "pozůstalost", "pozustalost"]),
        ("info", ["chci vědět", "chci vedet", "jak funguje", "jak to funguje"]),
    ]:
        for kw in kws:
            if kw in user_query and kw not in matched_keywords:
                matched_keywords.append(kw)

    payload: Dict[str, Any] = {
        "intent": dominant_intent,
        "domain": dominant_domain,
        "keywords": matched_keywords,
        "confidence": confidence,
        "raw_intent_scores": intent_scores,
        "raw_domain_scores": domain_scores,
    }

    notes: List[str] = [
        f"intent_engine: intent={dominant_intent}, domain={dominant_domain}, confidence={confidence}"
    ]

    return EngineOutput(
        name="intent_engine",
        payload=payload,
        notes=notes,
    )