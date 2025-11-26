"""
Judikatura engine – vyhledávání a vkládání judikatury do výstupu.

Tahle verze zatím NEUMÍ reálné online hledání.
Dává ale:
- jednotnou strukturu pro rozhodnutí (cases)
- stavy: OK / NONE_FOUND / CONFLICT / ERROR
- jednoduchou detekci rozporu v judikatuře
- hook pro budoucí "providers" (databáze, manuální zdroje, ...)

Pro testování a prototypování:
- do EngineInput.context můžeš dát klíč "debug_candidates"
  se seznamem pseudo-judikátů ve správném formátu – engine je vezme
  místo reálného hledání.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List
import json

from ..shared_types import EngineInput, EngineOutput
from runtime.config_loader import load_yaml, BASE_DIR
from llm.client import LLMClient, LLMMessage

# ---- Config + LLM klient ----

_CONFIG = load_yaml("engines/judikatura/config.yaml")

_llm_client: LLMClient | None = None


def _get_llm() -> LLMClient:
    """Lazy init LLM klienta, aby šel v testech případně mockovat."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


def _load_prompt(name: str) -> str:
    """Načte textový prompt z llm/prompts/."""
    prompt_path = BASE_DIR / "llm" / "prompts" / name
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


# ---- Datové typy pro vnitřní práci ----


@dataclass
class CaseLawItem:
    """
    Normalizovaná reprezentace jednoho rozhodnutí.

    Povinná pole (pro logiku engine):
    - id: interní nebo externí identifikátor
    - court_level: ns/nss/us/eslp/sdeu/other
    - reference: spisová značka / citace
    - year: rok vydání (int nebo None)
    - legal_issue: stručný popis otázky
    - holding_summary: shrnutí závěru
    - holding_direction: "pro_appellant" | "pro_defendant" | "mixed" | "other" | None
    - relevance_score: 0.0–1.0
    - source: textový popis zdroje (např. "NS ČR", "NSS", "ESLP HUDOC")
    """

    id: str
    court_level: str
    reference: str
    year: int | None
    legal_issue: str
    holding_summary: str
    holding_direction: str | None
    relevance_score: float
    source: str

    @staticmethod
    def from_dict(raw: Dict[str, Any]) -> "CaseLawItem":
        return CaseLawItem(
            id=str(raw.get("id", "")),
            court_level=str(raw.get("court_level", "other")).lower(),
            reference=str(raw.get("reference", "")),
            year=raw.get("year"),
            legal_issue=str(raw.get("legal_issue", "")),
            holding_summary=str(raw.get("holding_summary", "")),
            holding_direction=raw.get("holding_direction"),
            relevance_score=float(raw.get("relevance_score", 0.0)),
            source=str(raw.get("source", "")),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "court_level": self.court_level,
            "reference": self.reference,
            "year": self.year,
            "legal_issue": self.legal_issue,
            "holding_summary": self.holding_summary,
            "holding_direction": self.holding_direction,
            "relevance_score": self.relevance_score,
            "source": self.source,
        }


# ---- Pomocné funkce ----


def _get_effective_min_relevance(domain: str | None) -> float:
    """
    Do budoucna můžeš v domain_overrides v configu nastavit,
    že třeba pro trestní právo chceš vyšší práh relevance.
    """
    base = float(_CONFIG.get("min_relevance_score", 0.6))
    overrides = _CONFIG.get("domain_overrides", {}) or {}
    if domain and domain in overrides:
        domain_conf = overrides[domain] or {}
        return float(domain_conf.get("min_relevance_score", base))
    return base


def _collect_candidates(engine_input: EngineInput) -> List[CaseLawItem]:
    """
    Tady by jednou mělo být napojení na reálné zdroje judikatury.

    Aktuálně:
    - pokud je v context["debug_candidates"], použije se to
    - jinak vrátí prázdný seznam
    """
    debug_candidates = engine_input.context.get("debug_candidates")
    if isinstance(debug_candidates, list):
        return [CaseLawItem.from_dict(c) for c in debug_candidates]

    # TODO: sem přijde reálné napojení na zdroje (databáze, API, atd.)
    return []


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

    try:
        llm = _get_llm()
        raw = llm.chat(use_case="helper", messages=[system_msg, user_msg])
    except Exception:
        # Když LLM selže (API chyba, klíč chybí, ...), nic neměníme
        return item

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


def _filter_and_sort(cases: List[CaseLawItem], domain: str | None) -> List[CaseLawItem]:
    """
    Aplikuje relevanční práh, seřadí podle relevance a priorit zdrojů
    a omezí výsledky podle max_results a max_per_court_level.
    """
    if not cases:
        return []

    min_rel = _get_effective_min_relevance(domain)
    cfg = _CONFIG
    max_results = int(cfg.get("max_results", 5))
    max_per_level = int(cfg.get("max_per_court_level", 3))
    priority = cfg.get("sources_priority", []) or []

    # 1) filtr podle relevance
    filtered = [c for c in cases if c.relevance_score >= min_rel]
    if not filtered:
        return []

    # 2) seřadit podle priority zdroje + relevance
    def sort_key(item: CaseLawItem):
        try:
            prio_index = priority.index(item.court_level)
        except ValueError:
            prio_index = len(priority)
        year = item.year or 0
        return (prio_index, -item.relevance_score, -year)

    filtered.sort(key=sort_key)

    # 3) omezit počet na úrovni soudu
    per_level_count: Dict[str, int] = {}
    final: List[CaseLawItem] = []
    for c in filtered:
        level = c.court_level
        per_level_count.setdefault(level, 0)
        if per_level_count[level] >= max_per_level:
            continue
        final.append(c)
        per_level_count[level] += 1
        if len(final) >= max_results:
            break

    return final


def _detect_conflict(cases: List[CaseLawItem]) -> Dict[str, Any]:
    """
    Jednoduchá detekce konfliktu:
    - sleduje hodnotu holding_direction (např. pro_appellant / pro_defendant / mixed / other)
    - pokud existuje více než 1 významný směr, označí to jako CONFLICT
    """
    policy = _CONFIG.get("conflict_policy", {}) or {}
    if not policy.get("enabled", True):
        return {"conflict": False, "branches": []}

    if len(cases) < int(policy.get("require_min_cases", 2)):
        return {"conflict": False, "branches": []}

    max_branches = int(policy.get("max_branches", 3))

    branches: Dict[str, List[CaseLawItem]] = {}
    for c in cases:
        direction = c.holding_direction or "unknown"
        branches.setdefault(direction, []).append(c)

    # vyhoď 'unknown', pokud existují jiné smysluplné směry
    if len(branches) > 1 and "unknown" in branches:
        if any(k != "unknown" for k in branches.keys()):
            branches.pop("unknown", None)

    if len(branches) <= 1:
        return {"conflict": False, "branches": []}

    # připrav strukturu pro výstup (max_branches větví)
    conflict_branches: List[Dict[str, Any]] = []
    for direction, items in list(branches.items())[:max_branches]:
        conflict_branches.append(
            {
                "direction": direction,
                "count": len(items),
                "examples": [i.to_dict() for i in items[:2]],  # max 2 příklady na větev
            }
        )

    return {
        "conflict": True,
        "branches": conflict_branches,
    }


# ---- Hlavní entry point ----


def run(engine_input: EngineInput) -> EngineOutput:
    """
    Hlavní API funkce pro judikatura engine.
    """
    try:
        case = engine_input.context.get("case", {}) or {}
        domain = case.get("domain")

        # 1) kandidáti (debug nebo reálné zdroje)
        raw_candidates = _collect_candidates(engine_input)

        if not raw_candidates:
            # žádné kandidáty → NONE_FOUND
            return EngineOutput(
                name="judikatura_engine",
                payload={
                    "status": "NONE_FOUND",
                    "cases": [],
                    "message": (
                        "V této skeleton verzi nebyla nalezena žádná judikatura. "
                        "Později zde bude reálné vyhledávání ve zdrojích."
                    ),
                },
                notes=["judikatura_engine: no candidates (NONE_FOUND)."],
            )

        # 2) enrichment přes LLM (holding_direction / relevance)
        enriched_candidates: List[CaseLawItem] = []
        for c in raw_candidates:
            enriched = _enrich_with_llm(case, c)
            enriched_candidates.append(enriched)

        # 3) filtrace a řazení
        selected = _filter_and_sort(enriched_candidates, domain)
        if not selected:
            # kandidáti existovali, ale pod prahem relevance
            return EngineOutput(
                name="judikatura_engine",
                payload={
                    "status": "NONE_FOUND",
                    "cases": [],
                    "message": (
                        "Existují rozhodnutí s nízkou relevancí, ale pragmaticky se "
                        "nezobrazují. V plné verzi bude možné tuto hranici upravovat."
                    ),
                },
                notes=["judikatura_engine: candidates below relevance threshold (NONE_FOUND)."],
            )

        # 4) detekce konfliktu
        conflict_info = _detect_conflict(selected)
        if conflict_info.get("conflict"):
            status = "CONFLICT"
        else:
            status = "OK"

        payload = {
            "status": status,
            "cases": [c.to_dict() for c in selected],
            "conflict_info": conflict_info,
        }

        notes = [
            f"judikatura_engine: status={status}, selected_cases={len(selected)}",
        ]

        return EngineOutput(
            name="judikatura_engine",
            payload=payload,
            notes=notes,
        )

    except Exception as e:
        # fail-safe – raději přiznat chybu než mlžit
        return EngineOutput(
            name="judikatura_engine",
            payload={
                "status": "ERROR",
                "cases": [],
                "message": f"Judikatura engine narazil na chybu: {e}",
            },
            notes=["judikatura_engine: ERROR – viz message."],
        )
