"""
Core legal engine – hlavní právní rozbor.

Tahle verze NEdělá skutečné právo, ale dává ti strukturu, do které později
napojíš LLM (OpenAI API, atd.).

Cíl:
- issues (otázky)
- rules (právní úprava)
- analysis (aplikace na fakta)
- conclusion (závěr)
- certainty (HARD_FACT / REASONED_INFERENCE / SPECULATION)
"""

from __future__ import annotations

from typing import Any, Dict, List

from ..shared_types import EngineInput, EngineOutput
from runtime.config_loader import load_yaml


_CONFIG = load_yaml("engines/core_legal/config.yaml")


def _baseline_structure(case: Dict[str, Any]) -> Dict[str, Any]:
    """
    Vrátí základní IRAC strukturu – zatím generická, později ji
    nahradíš voláním LLM.
    """
    user_query = case.get("user_query", "")

    return {
        "issues": [
            {
                "label": "Hlavní právní otázka",
                "text": "Je třeba přesně identifikovat, jaká právní otázka je v jádru vašeho dotazu.",
                "derived_from": "user_query",
            }
        ],
        "rules": [
            {
                "label": "Relevantní právní úprava",
                "text": (
                    "V této skeleton verzi nejsou načtené konkrétní paragrafy. "
                    "V budoucnu zde bude odkaz na konkrétní ustanovení zákonů "
                    "podle zjištěné právní domény."
                ),
                "source_type": "HARD_FACT",
            }
        ],
        "analysis": [
            {
                "label": "Analýza (REASONED_INFERENCE)",
                "text": (
                    "Na základě stručného popisu situace bude v plné verzi "
                    "provedena aplikace právní úpravy na konkrétní fakta případu."
                ),
                "certainty": "REASONED_INFERENCE",
            }
        ],
        "conclusion": {
            "summary": (
                "Skeleton core_legal_engine: závěr zatím pouze naznačuje, "
                "že je potřeba doplnit fakta a zpřesnit právní kvalifikaci."
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


def run(engine_input: EngineInput) -> EngineOutput:
    case = engine_input.context.get("case", {})

    payload = _baseline_structure(case)

    notes: List[str] = [
        "core_legal_engine skeleton – zde bude hlavní právní rozbor pomocí LLM.",
        "Zatím se používá generická IRAC struktura (issues, rules, analysis, conclusion).",
    ]

    return EngineOutput(
        name="core_legal_engine",
        payload=payload,
        notes=notes,
    )
