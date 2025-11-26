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
from pathlib import Path
import json

from llm.client import LLMClient, LLMMessage
from runtime.config_loader import BASE_DIR

_CONFIG = load_yaml("engines/core_legal/config.yaml")

_llm_client: LLMClient | None = None


def _get_llm() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


def _load_prompt(name: str) -> str:
    prompt_path = BASE_DIR / "llm" / "prompts" / name
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

def _enrich_with_llm(case_context: Dict[str, Any], item: CaseLawItem) -> CaseLawItem:
    """
    Pokud item nemá holding_direction nebo relevance_score,
    zkusí je dopočítat pomocí LLM.
    """
    needs_direction = item.holding_direction is None
    needs_relevance = item.relevance_score == 0.0

    if not (needs_direction or needs_relevance):
        return item

    user_query = case_context.get("user_query", "")
    domain = case_context.get("domain", "unknown")

    base_prompt = _load_prompt("judikatura_classify.txt")

    decision_text_parts = [
        f"Soud: {item.source} ({item.court_level}), spis: {item.reference}, rok: {item.year}",
        f"Právní otázka/issue: {item.legal_issue}",
        f"Shrnutí rozhodnutí: {item.holding_summary}",
    ]
    decision_text = "\n".join(decision_text_parts)

    system_msg = LLMMessage(role="system", content=base_prompt)
    user_msg = LLMMessage(
        role="user",
        content=(
            f"Právní doména (orientačně): {domain}\n\n"
            f"Stručný popis situace od uživatele:\n{user_query}\n\n"
            f"Rozhodnutí soudu:\n{decision_text}"
        ),
    )

    llm = _get_llm()
    raw = llm.chat(use_case="helper", messages=[system_msg, user_msg])

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Když to nedá JSON, raději nic nepřepisovat
        return item

    # Bezpečné doplnění
    if needs_relevance:
        try:
            item.relevance_score = float(data.get("relevance_score", item.relevance_score))
        except (TypeError, ValueError):
            pass

    if needs_direction:
        direction = data.get("holding_direction")
        if isinstance(direction, str):
            item.holding_direction = direction

    # Normalizované shrnutí může přepsat původní summary, pokud chceš
    norm_summary = data.get("normalized_summary")
    if isinstance(norm_summary, str) and norm_summary.strip():
        item.holding_summary = norm_summary.strip()

    return item


raw_candidates = _collect_candidates(engine_input)

# enrichment přes LLM, pokud je dostupný a nechceš to vypnout
case = engine_input.context.get("case", {}) or {}
enriched_candidates: List[CaseLawItem] = []
for c in raw_candidates:
    enriched = _enrich_with_llm(case, c)
    enriched_candidates.append(enriched)

if not enriched_candidates:
    ...
selected = _filter_and_sort(enriched_candidates, domain)





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
