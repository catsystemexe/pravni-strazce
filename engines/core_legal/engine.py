# engines/core_legal/engine.py
"""
Core Legal Engine v1
--------------------

První plně funkční verze právního mozku systému.

Režimy:
- LLM nedostupné / vypnuté -> bezpečný skeleton fallback (původní IRAC struktura)
- LLM dostupné a povolené  -> skeleton IRAC + LLM hook pro závěr (conclusion_only)

Tím pádem:
- v produkci můžeš používat LLM,
- v testech / bez klíče vše běží dál přes skeleton.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from runtime.config_loader import load_yaml, BASE_DIR
from engines.domain_rules.loader import load_domain_profile
from engines.shared_types import EngineInput, EngineOutput

# V testech je LLMClient mockovaný – proto se importuje přímo.
from llm.client import LLMClient, LLMMessage

# Konstanty názvů enginů – aby se předešlo překlepům
ENGINE_NAME_LLM = "core_legal_engine_v1"
ENGINE_NAME_SKELETON = "core_legal_engine_skeleton"

# Konfigurace – ideálně existuje, ale když ne, engine nesmí spadnout
try:
    _CONFIG: Dict[str, Any] = load_yaml("engines/core_legal/config.yaml")
except Exception:
    _CONFIG = {}


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
    Wrapper pro jednotlivé LLM kroky.

    Načte:
    - správný prompt
    - temperature a max_tokens z configu (pokud existují)
    """
    prompt = _load_prompt(step)

    temp_cfg = _CONFIG.get("temperature", {}) or {}
    max_cfg = _CONFIG.get("max_tokens", {}) or {}

    temperature = temp_cfg.get(step)
    max_tokens = max_cfg.get(step)

    messages = [
        LLMMessage(role="system", content=prompt),
        LLMMessage(role="user", content=user_query),
    ]

    return llm.chat(
        use_case="legal_analysis",
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    ).strip()


# -----------------------------
# Fallback skeleton (bez LLM)
# -----------------------------


def _skeleton_irac(case: Dict[str, Any], error: Optional[str] = None) -> EngineOutput:
    """
    Skeleton verze – zachovává IRAC strukturu, aby:
    - testy zůstaly průchozí,
    - runtime nepadal, když není LLM dostupné.

    Test `test_core_legal_engine_skeleton_has_llm_error_if_no_llm`
    vyžaduje, aby byl v payloadu vždy klíč `llm_error`.
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

    # llm_error musí být vždy přítomen
    if error:
        payload["llm_error"] = str(error)
    else:
        payload["llm_error"] = "LLM režim je vypnutý nebo není dostupný."

    notes: List[str] = [
        "core_legal_engine skeleton fallback – LLM není dostupné nebo selhalo.",
        "Zachována IRAC struktura kvůli kompatibilitě s testy a orchestrátorem.",
    ]

    return EngineOutput(
        name=ENGINE_NAME_SKELETON,
        payload=payload,
        notes=notes,
    )


# -----------------------------
# Hlavní LLM-based běh
# -----------------------------


def run(engine_input: EngineInput) -> EngineOutput:
    """
    Core Legal Engine – LLM hook v1

    Režimy:
    - LLM vypnuto (default):
        -> čistý skeleton IRAC (bez nákladů, bezpečné, test-friendly)
    - LLM zapnuto (CORE_LEGAL_USE_LLM=1 nebo context["use_llm"]=True):
        -> skeleton IRAC + LLM hook pro závěr (conclusion_only)
    """
    ctx = engine_input.context or {}
    case = ctx.get("case", {}) or {}

    user_query: str = case.get("user_query", "") or ""
    domain: str = case.get("domain") or "unknown"

    # 1) Rozhodnutí, zda použít LLM (context nebo env proměnná)
    use_llm_ctx = bool(ctx.get("use_llm"))
    use_llm_env = os.getenv("CORE_LEGAL_USE_LLM", "").lower() in ("1", "true", "yes")
    use_llm = use_llm_ctx or use_llm_env

    # Pokud není LLM explicitně povolené, vracíme skeleton
    if not use_llm:
        return _skeleton_irac(case)

    # 2) LLM hook – pouze závěr (conclusion)
    llm_error: Optional[str] = None

    try:
        llm = LLMClient()
    except Exception as e:
        # Když nejde vytvořit klient, bezpečně spadneme do skeletonu
        return _skeleton_irac(case, error=f"LLMClient init error: {e}")

    # Zkusíme přes LLM získat závěr
    try:
        # prompt "conclusion" musí být v engines/core_legal/prompts/conclusion.md
        llm_conclusion = _ask_step(llm, "conclusion", user_query)
    except Exception as e:
        llm_error = f"Chyba při získání závěru z LLM: {e}"
        return _skeleton_irac(case, error=llm_error)

    # Certainty je „soft“ – při chybě použijeme rozumný default
    try:
        llm_certainty = _ask_step(llm, "certainty", user_query)
    except Exception:
        llm_certainty = "REASONED_INFERENCE"

    # doménový profil (pokud existuje)
    try:
        domain_profile = load_domain_profile(domain)
    except Exception:
        domain_profile = None

    # 3) Postavíme payload: skeleton IRAC + LLM závěr
    payload: Dict[str, Any] = {
        # Issues – skeleton, navázaný na user_query
        "issues": [
            {
                "label": "Hlavní právní otázka",
                "text": (
                    "Tato verze jádra doplňuje závěr pomocí LLM, "
                    "ale právní otázka je odvozena přímo z popisu situace."
                ),
                "derived_from": "user_query",
                "raw_text": user_query,
            }
        ],
        # Rules – stále skeleton
        "rules": [
            {
                "label": "Relevantní právní úprava",
                "text": (
                    "V této pilotní LLM verzi nejsou načteny konkrétní paragrafy. "
                    "Plná verze zde může uvádět konkrétní ustanovení podle "
                    "detekované právní domény."
                ),
                "source_type": "HARD_FACT",
            }
        ],
        # Analysis – skeleton, s poznámkou o LLM hooku
        "analysis": [
            {
                "label": "Analýza (REASONED_INFERENCE)",
                "text": (
                    "Analytická část zatím využívá skeleton přístup. LLM hook je zaměřen "
                    "primárně na formulaci shrnujícího závěru, nikoli na celou IRAC analýzu."
                ),
                "certainty": "REASONED_INFERENCE",
            }
        ],
        # Conclusion – hlavní přidaná hodnota LLM
        "conclusion": {
            "summary": llm_conclusion,
            "certainty": llm_certainty or "REASONED_INFERENCE",
        },
        "meta": {
            "domain": domain,
            "risk_level": case.get("risk_level", "unknown"),
            "intent": case.get("intent", "unknown"),
            "config_domains": _CONFIG.get("domains", []),
            "llm_mode": "conclusion_only",
        },
    }

    if domain_profile:
        payload["domain_profile"] = domain_profile

    if llm_error:
        payload["llm_error"] = llm_error

    notes: List[str] = [
        "core_legal_engine LLM hook: conclusion_only (ostatní části skeleton).",
    ]

    return EngineOutput(
        name=ENGINE_NAME_LLM,
        payload=payload,
        notes=notes,
    )