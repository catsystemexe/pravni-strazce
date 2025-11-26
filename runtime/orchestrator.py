"""
Runtime orchestrátor – hlavní pipeline:

1. role_detection
2. intent_detection
3. domain & risk routing
4. spuštění core_legal_engine
5. judikatura + safety
6. složení výstupu přes modular_output_system

Zatím pořád skeleton, ale architekturou už připravené na reálné enginy.
"""

from __future__ import annotations

from typing import Dict, List

from .context import (
    CaseContext,
    EngineResult,
    UserRole,
    LegalDomain,
    RiskLevel,
    UserIntent,
)
from .config_loader import load_yaml

from engines.shared_types import EngineInput
from engines.core_legal import engine as core_legal_engine
from engines.judikatura import engine as judikatura_engine
from engines.safety import legal_safety_layer, pii_guard
from engines.output import modular_output


# --- Konfigurace produktu (e-advokat PRO) ---


_PRODUCT_CONFIG = load_yaml("product/e_advokat_pro/product.yaml")
_FEATURE_FLAGS = load_yaml("product/e_advokat_pro/feature_flags.yaml")
_RISK_POLICY = load_yaml("product/e_advokat_pro/risk_policy.yaml")


# --- Jednoduché heuristiky (zatím bez LLM) ---


def _detect_role(user_query: str) -> UserRole:
    # TODO: později můžeš nahradit LLM / patterny
    if "jsem advokát" in user_query.lower():
        return UserRole.ADVOKAT
    return UserRole.CLIENT


def _detect_intent(user_query: str) -> UserIntent:
    q = user_query.lower()
    if "sepsat" in q or "napiš" in q or "podání" in q:
        return UserIntent.DOCUMENT_DRAFTING
    if "jak mám postupovat" in q or "co mám dělat" in q:
        return UserIntent.PROCEDURAL_STRATEGY
    if "smlouva" in q or "kontrakt" in q:
        return UserIntent.CONTRACT_REVIEW
    if "judikatura" in q or "rozhodnutí soudu" in q:
        return UserIntent.CASE_LAW_LOOKUP
    if "doporuč, jak napsat" in q or "jak to říct" in q:
        return UserIntent.STRATEGY_COACH
    # default
    return UserIntent.LEGAL_EXPLANATION


def _detect_domain(user_query: str) -> LegalDomain:
    q = user_query.lower()
    if "rozvod" in q or "péče o dítě" in q or "ospod" in q:
        return LegalDomain.RODINA
    if "trestní" in q or "trestný čin" in q or "obžaloba" in q:
        return LegalDomain.TRESTNI
    if "pracovní smlouva" in q or "výpověď z práce" in q:
        return LegalDomain.PRACOVNI
    if "reklamace" in q or "spotřebitel" in q:
        return LegalDomain.SPOTREBITELSKE
    # default na civil
    return LegalDomain.CIVIL


def _map_domain_to_risk(domain: LegalDomain) -> RiskLevel:
    mapping = _RISK_POLICY.get("risk_mapping", {})
    level_str = mapping.get(domain.value, "medium")
    try:
        return RiskLevel(level_str)
    except ValueError:
        return RiskLevel.MEDIUM


# --- Hlavní pipeline ---


def run_pipeline(user_query: str) -> Dict:
    """
    Entry point pro core agenta.
    """
    # 1) Naplnit kontext základními odhady
    ctx = CaseContext(
        user_query=user_query,
        role=_detect_role(user_query),
        intent=_detect_intent(user_query),
        domain=_detect_domain(user_query),
    )
    ctx.risk_level = _map_domain_to_risk(ctx.domain)

    engine_results: List[EngineResult] = []

    # 2) Core legal engine
    core_input = EngineInput(context={"case": ctx.to_dict()})
    core_out = core_legal_engine.run(core_input)
    engine_results.append(
        EngineResult(name=core_out.name, data=core_out.payload, notes=core_out.notes)
    )

    # 3) Judikatura (pokud zapnutá)
    if _FEATURE_FLAGS["features"].get("judikatura_engine", True):
        judik_input = EngineInput(
            context={"case": ctx.to_dict(), "core_legal": core_out.payload}
        )
        judik_out = judikatura_engine.run(judik_input)
        engine_results.append(
            EngineResult(name=judik_out.name, data=judik_out.payload, notes=judik_out.notes)
        )

    # 4) Safety – PII + legal safety layer
    if _FEATURE_FLAGS["features"].get("pii_guard", True):
        pii_input = EngineInput(
            context={
                "case": ctx.to_dict(),
                "engine_results": [r.to_dict() for r in engine_results],
            }
        )
        pii_out = pii_guard.run(pii_input)
        engine_results.append(
            EngineResult(name=pii_out.name, data=pii_out.payload, notes=pii_out.notes)
        )

    if _FEATURE_FLAGS["features"].get("legal_safety_layer", True):
        safety_input = EngineInput(
            context={
                "case": ctx.to_dict(),
                "engine_results": [r.to_dict() for r in engine_results],
            }
        )
        safety_out = legal_safety_layer.run(safety_input)
        engine_results.append(
            EngineResult(name=safety_out.name, data=safety_out.payload, notes=safety_out.notes)
        )

    # 5) Modular output – složit finální odpověď
    output_input = EngineInput(
        context={
            "case": ctx.to_dict(),
            "engine_results": [r.to_dict() for r in engine_results],
        }
    )
    final_out = modular_output.run(output_input)

    return {
        "context": ctx.to_dict(),
        "engine_results": [r.to_dict() for r in engine_results],
        "final_answer": final_out.payload.get("rendered_text", ""),
        "notes": final_out.notes,
    }
