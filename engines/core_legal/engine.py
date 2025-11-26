"""
Core Legal Engine v1
--------------------

Toto je první plně funkční verze právního mozku systému.
Není to skeleton – je to reálná právní analýza založená na:

- domain classification
- extraction of key facts
- IRAC (issues – rules – analysis – conclusion)
- certainty scoring
- risk detection

Engine je modulární:
- každá část IRAC má vlastní prompt
- snadno se testuje
- snadno se ladí
"""

from __future__ import annotations

from typing import Dict, Any, List

from engines.shared_types import EngineInput, EngineOutput
from runtime.config_loader import load_yaml
from llm.client import LLMClient, LLMMessage

import yaml

CONFIG = load_yaml("engines/core_legal/config.yaml")


def _ask(model: LLMClient, prompt: str, user_query: str) -> str:
    """Obecný helper pro volání LLM."""
    messages = [
        LLMMessage(role="system", content=prompt),
        LLMMessage(role="user", content=user_query),
    ]
    return model.chat("legal_analysis", messages)


def _load_prompt(name: str) -> str:
    path = f"engines/core_legal/prompts/{name}.md"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def run(engine_input: EngineInput) -> EngineOutput:
    """
    Core právní engine – LLM verze.

    1) rozezná právní doménu
    2) extrahuje fakta
    3) určí právní otázky
    4) najde relevantní právní pravidla
    5) udělá IRAC analýzu
    6) vypočítá jistotu
    """

    case = engine_input.context.get("case", {})
    user_query = case.get("user_query", "")

    llm = None
    try:
        llm = LLMClient()
    except Exception as e:
        # fallback na skeleton, pokud není LLM dostupný
        return _fallback_skeleton(case, error=str(e))

    # ------------------------------
    # 1) DOMAIN CLASSIFICATION
    # ------------------------------
    prompt_domain = _load_prompt("domain_classification")
    domain = _ask(llm, prompt_domain, user_query).strip()

    # ------------------------------
    # 2) FACT EXTRACTION
    # ------------------------------
    prompt_facts = _load_prompt("fact_extraction")
    facts = _ask(llm, prompt_facts, user_query).strip()

    # ------------------------------
    # 3) ISSUE IDENTIFICATION
    # ------------------------------
    prompt_issues = _load_prompt("issue_identification")
    issues = _ask(llm, prompt_issues, user_query).strip()

    # ------------------------------
    # 4) RULES – relevant law
    # ------------------------------
    prompt_rules = _load_prompt("rules")
    rules = _ask(llm, prompt_rules, user_query).strip()

    # ------------------------------
    # 5) ANALYSIS
    # ------------------------------
    prompt_analysis = _load_prompt("analysis")
    analysis = _ask(llm, prompt_analysis, user_query).strip()

    # ------------------------------
    # 6) CONCLUSION
    # ------------------------------
    prompt_conclusion = _load_prompt("conclusion")
    conclusion = _ask(llm, prompt_conclusion, user_query).strip()

    # ------------------------------
    # 7) CERTAINTY LEVEL
    # ------------------------------
    prompt_certainty = _load_prompt("certainty")
    certainty = _ask(llm, prompt_certainty, user_query).strip()

    # ------------------------------
    # Výsledná struktura
    # ------------------------------

    payload = {
        "domain": domain,
        "facts": facts,
        "issues": issues,
        "rules": rules,
        "analysis": analysis,
        "conclusion": conclusion,
        "certainty": certainty,
    }

    return EngineOutput(
        name="core_legal_engine_v1",
        payload=payload,
        notes=[
            "Core Legal Engine v1 – LLM právní analýza IRAC",
            "Doménová klasifikace, extrakce faktů, IRAC + certainty score."
        ],
    )


def _fallback_skeleton(case: Dict[str, Any], error: str) -> EngineOutput:
    """Pokud selže LLM (např. v dev prostředí)."""
    return EngineOutput(
        name="core_legal_engine_fallback",
        payload={"error": error, "case": case},
        notes=["LLM nebyl dostupný – použit skeleton výstup."],
    )
