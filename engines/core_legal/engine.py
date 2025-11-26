"""
Core Legal Engine v1
--------------------

První plně funkční verze právního mozku systému.

Režimy:
- LLM dostupné  -> plná IRAC analýza přes prompty (domain, facts, issues, rules, analysis, conclusion, certainty)
- LLM nedostupné -> bezpečný skeleton fallback (původní IRAC struktura)

Tím pádem:
- v produkci můžeš používat LLM,
- v testech / bez klíče vše běží dál přes skeleton.
"""

from __future__ import annotations

from typing import Any, Dict, List

from ..shared_types import EngineInput, EngineOutput
from runtime.config_loader import load_yaml, BASE_DIR
from llm.client import LLMClient, LLMMessage


_CONFIG = load_yaml("engines/core_legal/config.yaml")


# -----------------------------
# Pomocné funkce
# -----------------------------


def _load_prompt(name: str) -> str:
    """
    Načte prompt pro daný krok z:
    engines/core_legal/prompts/<name>.md
    """
    path = BASE_DIR / "engines" / "core_legal" / "prompts" / f"{name}.md"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _ask_step(llm: LLMClient, step: str, user_query: str) -> str:
    """
    Obecný wrapper pro jednotlivé kroky (domain, facts, issues, ...).
    Zatím používá jednotný use_case 'legal_analysis'.
    """
    prompt = _load_prompt(step)
    messages = [
        LLMMessage(role="system", content=prompt),
        LLMMessage(role="user", content=user_query),
    ]
    # Do budoucna můžeš podle _CONFIG řídit teplotu / max_tokens na úrovni LLMClient
    return llm.chat(use_case="legal_analysis", messages=messages).strip()


# -----------------------------
# Fallback skeleton (bez LLM)
# -----------------------------


def _skeleton_irac(case: Dict[str, Any], error: str | None = None) -> EngineOutput:
    """
    Původní skeleton verze – zachovává IRAC strukturu, aby:
    - testy zůstaly průchozí,
    - runtime nepadal, když není LLM dostupné.
    """
    user_query = case.get("user_query", "")

    payload: Dict[str, Any] = {
        "issues": [
            {
                "label": "Hlavní právní otázka",
                "text": (
                    "Skeleton verze core_legal_engine – místo plné analýzy je zde "
                    "pouze obecný popis hlavní právní otázky. "
                    "Plná verze využívá LLM k přesnému pojmenování problému."
                ),
                "derived_from": "user_query",
                "raw_text": user_query,
            }
        ],
        "rules": [
            {
                "label": "Relevantní právní úprava",
                "text": (
                    "V této skeleton verzi nejsou načtené konkrétní paragrafy. "
                    "V plné verzi zde budou konkrétní ustanovení zákonů podle "
                    "detekované právní domény (občanské, trestní, rodinné, ...)."
                ),
                "source_type": "HARD_FACT",
            }
        ],
        "analysis": [
            {
                "label": "Analýza (REASONED_INFERENCE)",
                "text": (
                    "Na základě stručného popisu situace bude v plné verzi provedena "
                    "aplikace právní úpravy na konkrétní fakta případu. "
                    "Tahle skeleton verze jen drží strukturu pro budoucí výstup."
                ),
                "certainty": "REASONED_INFERENCE",
            }
        ],
        "conclusion": {
            "summary": (
                "Skeleton core_legal_engine: závěr zatím pouze naznačuje, "
                "že je potřeba doplnit fakta a zpřesnit právní kvalifikaci. "
                "Plná verze nabídne konkrétnější odpověď a doporučený postup."
            ),
            "certainty": "REASONED_INFERENCE",
        },
        "meta": {
            "domain": case.get("domain", "unknown"),
            "risk_level": case.get("risk_level", "unknown"),
            "intent": case.get("intent", "unknown"),
            "config_domains": _CONFIG.get("domains", []),
        },
    }

    if error:
        payload["llm_error"] = str(error)

    notes: List[str] = [
        "core_legal_engine skeleton fallback – LLM není dostupné nebo selhalo.",
        "Zachována IRAC struktura kvůli kompatibilitě s testy a orchestrátorem.",
    ]

    return EngineOutput(
        name="core_legal_engine_skeleton",
        payload=payload,
        notes=notes,
    )


# -----------------------------
# Hlavní LLM-based běh
# -----------------------------


def run(engine_input: EngineInput) -> EngineOutput:
    """
    Hlavní entry point Core Legal Engine.

    Tok:
    1) pokus o inicializaci LLMClient
       - pokud selže: skeleton fallback
    2) zavolání jednotlivých kroků přes prompty:
       - domain_classification
       - fact_extraction
       - issue_identification
       - rules
       - analysis
       - conclusion
       - certainty
    3) složení IRAC payloadu pro orchestrátor
    """
    case = engine_input.context.get("case", {}) or {}
    user_query = case.get("user_query", "")

    # 1) LLM klient – pokud není k dispozici, spadneme do skeletonu
    try:
        llm = LLMClient()
    except Exception as e:
        return _skeleton_irac(case, error=str(e))

    # 2) Jednotlivé kroky IRAC pipeline

    # a) Doména práva
    domain = _ask_step(llm, "domain_classification", user_query)

    # b) Fakta
    facts = _ask_step(llm, "fact_extraction", user_query)

    # c) Issues
    issues = _ask_step(llm, "issue_identification", user_query)

    # d) Rules
    rules = _ask_step(llm, "rules", user_query)

    # e) Analysis
    analysis = _ask_step(llm, "analysis", user_query)

    # f) Conclusion
    conclusion = _ask_step(llm, "conclusion", user_query)

    # g) Certainty
    certainty = _ask_step(llm, "certainty", user_query)

    # 3) Výsledný payload – LLM verze

    payload: Dict[str, Any] = {
        "domain": domain,
        "facts": facts,
        "issues": issues,
        "rules": rules,
        "analysis": analysis,
        "conclusion": conclusion,
        "certainty": certainty,
        "meta": {
            "config_domains": _CONFIG.get("domains", []),
        },
    }

    notes: List[str] = [
        "core_legal_engine v1 – LLM právní analýza (IRAC).",
        "Kroky: domain, facts, issues, rules, analysis, conclusion, certainty.",
    ]

    return EngineOutput(
        name="core_legal_engine_v1",
        payload=payload,
        notes=notes,
    )
