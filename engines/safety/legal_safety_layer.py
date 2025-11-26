"""
Legal safety layer – řízení rizikovosti, blokace nebezpečných odpovědí,
omezení kreativních závěrů u high-risk domén.

V téhle verzi:
- NEblokuje ještě nic tvrdě
- jen přidává doporučení a flagy podle risk_level
"""

from __future__ import annotations

from typing import Any, Dict, List

from ..shared_types import EngineInput, EngineOutput
from runtime.config_loader import load_yaml


_CONFIG = load_yaml("engines/safety/config.yaml")


def _decide(case: Dict[str, Any]) -> Dict[str, Any]:
    risk_level = case.get("risk_level", "unknown")
    role = case.get("role", "client")

    profiles = _CONFIG.get("risk_profiles", {})
    profile = profiles.get(risk_level, profiles.get("medium", {}))

    decision = "allow"
    warnings: List[str] = []

    if risk_level == "high":
        warnings.append(
            "High-risk oblast (např. trestní nebo rodinné právo) – důrazně doporučeno konzultovat reálného advokáta."
        )
        if role == "client":
            warnings.append(
                "Jste laik (role=client). Neopírejte se pouze o výstup AI, berte jej jako podklad pro konzultaci."
            )

    if not profile.get("allow_reasoned_inference", True):
        warnings.append(
            "Odvozené závěry (reasoned inference) by měly být výrazně omezeny – držet se pouze jistých faktů a textu zákona."
        )

    return {
        "decision": decision,
        "profile": profile,
        "risk_level": risk_level,
        "warnings": warnings,
    }


def run(engine_input: EngineInput) -> EngineOutput:
    case = engine_input.context.get("case", {})
    result = _decide(case)

    notes = ["legal_safety_layer skeleton – zatím jen přidává upozornění podle rizika."]

    return EngineOutput(
        name="legal_safety_layer",
        payload=result,
        notes=notes,
    )
