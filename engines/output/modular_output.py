"""
Modular output system – skládá finální odpověď z jednotlivých bloků.

V téhle verzi:
- vytáhne základ z core_legal_engine + judikatura + safety
- vloží je do šablony templates/answers/legal_answer_with_judikatura.md
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from ..shared_types import EngineInput, EngineOutput
from runtime.config_loader import BASE_DIR, load_yaml


_CONFIG = load_yaml("engines/output/config.yaml")


def _find_engine_result(engine_results: List[Dict[str, Any]], name: str) -> Dict[str, Any]:
    for r in engine_results:
        if r.get("name") == name:
            return r.get("data", {})
    return {}


def _load_template() -> str:
    rel_path = _CONFIG["templates"]["default_answer"]
    full_path = BASE_DIR / "templates" / "answers" / Path(rel_path).name
    with open(full_path, "r", encoding="utf-8") as f:
        return f.read()


def run(engine_input: EngineInput) -> EngineOutput:
    ctx = engine_input.context.get("case", {})
    engine_results = engine_input.context.get("engine_results", [])

    core_data = _find_engine_result(engine_results, "core_legal_engine")
    judik_data = _find_engine_result(engine_results, "judikatura_engine")
    safety_data = _find_engine_result(engine_results, "legal_safety_layer")

    template = _load_template()

    # --- Sestav obsah jednotlivých bloků (zatím hodně jednoduché) ---

    executive_summary = (
        "Skeleton verze: shrnutí bude v budoucnu generováno na základě závěru "
        "z core_legal_engine a safety layeru.\n"
    )

    legal_analysis = ""
    for issue in core_data.get("issues", []):
        legal_analysis += f"### {issue.get('label', 'Otázka')}\n{issue.get('text', '')}\n\n"
    for rule in core_data.get("rules", []):
        legal_analysis += f"**{rule.get('label', 'Právní úprava')}:** {rule.get('text', '')}\n\n"
    for ana in core_data.get("analysis", []):
        legal_analysis += f"**Analýza:** {ana.get('text', '')}\n\n"

    judik_block = ""
    status = judik_data.get("status", "NONE_FOUND")
    if status == "OK":
        judik_block += "Byla nalezena relevantní judikatura:\n\n"
        for c in judik_data.get("cases", []):
            judik_block += f"- {c.get('court', 'Soud')} {c.get('reference', '')}: {c.get('summary', '')}\n"
    elif status == "CONFLICT":
        judik_block += (
            "Judikatura není jednotná, existují různé linie rozhodování. "
            "V plné verzi zde bude detailnější rozbor.\n"
        )
    else:
        judik_block += (
            "V téhle skeleton verzi není implementováno vyhledávání judikatury. "
            "Později zde bude informace, zda existuje přímé rozhodnutí k dané situaci.\n"
        )

    risks_block = ""
    if safety_data:
        risk_level = safety_data.get("risk_level", "unknown")
        warnings = safety_data.get("warnings", [])
        risks_block += f"- Úroveň rizika: **{risk_level}**\n"
        if warnings:
            risks_block += "\n".join(f"- {w}" for w in warnings)

    next_steps = (
        "Skeleton verze: v plné verzi zde budou konkrétní doporučené kroky "
        "(co teď můžeš udělat, jaká podání zvážit, kdy jít za advokátem).\n"
    )

    rendered = (
        template.replace("(tady přijde stručné shrnutí odpovědi pro laika)", executive_summary)
        .replace("(tady přijde strukturovaná analýza – právní úprava, aplikace na fakta, závěr)", legal_analysis)
        .replace("(tady se vloží relevantní rozhodnutí, nebo jasná informace, že žádná přímá judikatura není)", judik_block)
        .replace("(tady přijde výčet rizik, nejasností a rozporných výkladů)", risks_block)
        .replace("(tady přijde doporučený postup pro uživatele)", next_steps)
    )

    notes = ["modular_output_system skeleton – skládá text z core_legal, judikatury a safety."]

    return EngineOutput(
        name="modular_output_system",
        payload={"rendered_text": rendered},
        notes=notes,
    )
