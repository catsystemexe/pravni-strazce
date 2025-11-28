from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from engines.shared_types import EngineInput, EngineOutput
from runtime.config_loader import load_yaml

# LLM klient – děláme import "best-effort", aby to nespadlo v prostředí bez LLM.
try:
    from llm.client import LLMClient, LLMMessage  # stejný jako u core_legal
except Exception:  # pragma: no cover - v testovacím/skeleton prostředí
    LLMClient = None  # type: ignore[assignment]
    LLMMessage = None  # type: ignore[assignment]

PROMPT_PATH = Path(__file__).parent / "prompts" / "risk_assessment.md"


# -------------------------------------------------------
# Pomocné funkce pro LLM hook
# -------------------------------------------------------


def _load_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        return "RISK ENGINE PROMPT ERROR: file not found."


def _llm_risk_analysis(case: Dict[str, Any]) -> Dict[str, Any]:
    """
    LLM hook — volitelné doplnění risk analýzy pomocí LLM.

    Pokud:
    - není dostupný LLMClient, nebo
    - dojde k chybě,
    vrací prázdný dict a Risk engine běží čistě heuristicky.
    """
    if LLMClient is None or LLMMessage is None:
        return {}

    prompt = _load_prompt()

    text = f"""
{prompt}

/STRUCTURED_OUTPUT
/NO_HALLUCINATIONS
/ASK_FOR_MISSING_FACTS

UŽIVATELSKÝ POPIS:
\"\"\"{case.get('user_query', '')}\"\"\"
"""

    try:
        llm = LLMClient()
        messages = [
            LLMMessage(role="system", content=text),
        ]
        out = llm.chat(
            use_case="risk_analysis",
            messages=messages,
            temperature=0.0,
        )
        # Očekáváme JSON-like výstup; pokud přijde něco jiného, prostě to ignorujeme.
        if isinstance(out, dict):
            return out
        return {}
    except Exception:
        return {}


# -------------------------------------------------------
# Konfigurace
# -------------------------------------------------------

try:
    _CONFIG: Dict[str, Any] = load_yaml("engines/risk/config.yaml")
except Exception:
    _CONFIG = {}

# Default váhy + klíčová slova pro jednotlivé dimenze rizika.
# Jsou navržené tak, aby zachovaly původní chování testů:
#  - "lhůta"      -> deadline_sensitive (váha 3)
#  - "obvinění"   -> criminal_sensitive (váha 3)
#  - "nezletilé"/"dítě" -> child_sensitive (váha 3)
# Celkové skóre 3+3+3 = 9 -> level == HIGH
_DEFAULT_RULES: List[Dict[str, Any]] = [
    {
        "flag": "deadline_sensitive",
        "dimension": "procedural",
        "weight": 3,
        "keywords": [
            r"\blhůta\b",
            r"\bdo\s+\d+\s*dní\b",
            r"\bodvolání\b",
            r"\bstížnost\b",
            r"\btermín\b",
            r"\bpromlčen[íy]\b",
        ],
    },
    {
        "flag": "criminal_sensitive",
        "dimension": "criminal",
        "weight": 3,
        "keywords": [
            r"\bobviněn[íy]?\b",
            r"\btrestn[íy]\s+stíhán[íy]?\b",
            r"\btrestn[íy]\s+čin\b",
            r"\bpolicie\b",
            r"\bPČR\b",
        ],
    },
    {
        "flag": "child_sensitive",
        "dimension": "child",
        "weight": 3,
        "keywords": [
            r"\bnezletil[áéý]\b",
            r"\bdít[eě]\b",
            r"\bdcera\b",
            r"\bsyn\b",
            r"\bžák\b",
            r"\bžákyně\b",
            r"\bškola\b",
            r"\bOSPOD\b",
        ],
    },
    # Další dimenze – už nejsou testy vázané, ale hodí se pro reálný provoz
    {
        "flag": "authority_sensitive",
        "dimension": "authority",
        "weight": 2,
        "keywords": [
            r"\bsoud\b",
            r"\bstátní zástupkyn[ěe]\b",
            r"\bředitel\b",
            r"\búřad\b",
        ],
    },
    {
        "flag": "financial_impact",
        "dimension": "financial",
        "weight": 2,
        "keywords": [
            r"\bškod[ay]\b",
            r"\bnáhrada\b",
            r"\bexekuce\b",
            r"\bzadlužen[íy]\b",
        ],
    },
]

# Možnost doplnit / přepsat defaultní pravidla z YAML
_EXTRA_RULES: List[Dict[str, Any]] = _CONFIG.get("extra_rules", [])
_RISK_RULES: List[Dict[str, Any]] = _DEFAULT_RULES + _EXTRA_RULES


# -------------------------------------------------------
# Pomocné funkce – heuristiky
# -------------------------------------------------------


def _normalize_text(s: str) -> str:
    return " ".join((s or "").split())


def _match_keywords(text: str, patterns: List[str]) -> List[str]:
    hits: List[str] = []
    for pat in patterns:
        if re.search(pat, text, flags=re.IGNORECASE):
            hits.append(pat)
    return hits


def _collect_flags(text: str, case: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Jádro heuristiky:
    - projde všechny definované RULES
    - pokud najde shodu na klíčových slovech, vytvoří flag
    - v budoucnu sem můžeš přidat další logiku (kombinace signálů, kontext atd.)
    """
    flags: List[Dict[str, Any]] = []

    for rule in _RISK_RULES:
        patterns: List[str] = rule.get("keywords", [])
        hits = _match_keywords(text, patterns)

        if not hits:
            continue

        weight: int = int(rule.get("weight", 1))
        # jednoduchý boost, pokud je víc než jedno trefené klíčové slovo v rámci jedné dimenze
        if len(hits) > 1:
            weight += 1

        flags.append(
            {
                "flag": rule["flag"],
                "dimension": rule.get("dimension", "generic"),
                "weight": weight,
                "keywords_hit": hits,
            }
        )

    return flags


def _score_to_level(score: int) -> str:
    """
    Mapování skóre -> úroveň rizika.
    Nastavené tak, aby:
    - 0–3   -> LOW
    - 4–7   -> MEDIUM
    - 8+    -> HIGH
    """
    if score <= 3:
        return "LOW"
    if score <= 7:
        return "MEDIUM"
    return "HIGH"


def _aggregate_dimensions(flags: List[Dict[str, Any]]) -> Dict[str, int]:
    dims: Dict[str, int] = {}
    for f in flags:
        dim = f.get("dimension", "generic")
        dims[dim] = dims.get(dim, 0) + int(f.get("weight", 1))
    return dims


def _adjust_score(
    base_score: int,
    dimensions: Dict[str, int],
    intent: Optional[str],
    domain: Optional[str],
) -> int:
    """
    Risk Engine v2 – úprava základního skóre podle intentu a domény.

    base_score:
        součet vah z klíčových slov (původní chování)
    dimensions:
        agregované dimenze (criminal / child / procedural / ...)
    intent, domain:
        heuristická klasifikace z intent_engine / core.meta
    """
    score = base_score

    # -------------------------
    # Domain-based úpravy
    # -------------------------
    if domain == "criminal":
        # trestní věci jsou obecně vážnější
        score += dimensions.get("criminal", 0) * 2
        score += 2  # základní offset

    if domain == "school":
        # spory se školou typicky zasahují dítě + autoritu
        score += dimensions.get("child", 0)
        score += dimensions.get("authority", 0)

    if domain == "family":
        # rodinné věci s dětmi
        score += int(dimensions.get("child", 0) * 1.5)

    if domain == "inheritance":
        # dědictví – procesní stránka klíčová, criminal často false positive
        score += dimensions.get("procedural", 0) * 2
        score -= dimensions.get("criminal", 0)

    if domain == "administrative":
        score += int(dimensions.get("procedural", 0) * 1.5)

    # -------------------------
    # Intent-based úpravy
    # -------------------------
    if intent == "complaint":
        # stížnosti / odvolání – procesní závažnost
        score += 2
        score += dimensions.get("procedural", 0)

    if intent == "criminal_defense":
        # obrana v trestním řízení – vždy vážné
        score += 4

    if intent == "school_dispute":
        score += dimensions.get("child", 0)
        score += dimensions.get("authority", 0)

    if intent == "inheritance":
        score += dimensions.get("procedural", 0)
        score -= dimensions.get("criminal", 0)

    if intent == "document_check":
        # kontrola dokumentu/smlouvy – typicky menší urgentnost
        score -= 2
        score -= dimensions.get("criminal", 0)

    # Žádné záporné skóre
    if score < 0:
        score = 0

    return int(score)


# -------------------------------------------------------
# Hlavní vstupní bod
# -------------------------------------------------------


def run(engine_input: EngineInput) -> EngineOutput:
    ctx = engine_input.context or {}
    case: Dict[str, Any] = ctx.get("case", {}) or {}

    # Intent/domain můžeme získat z contextu nebo z core.meta
    core = ctx.get("core", {}) or {}
    core_meta = core.get("meta", {}) if isinstance(core, dict) else {}

    intent: Optional[str] = ctx.get("intent") or core_meta.get("intent")
    domain: Optional[str] = ctx.get("domain") or core_meta.get("domain")

    user_query: str = _normalize_text(case.get("user_query", ""))
    extra_context_pieces: List[str] = []

    # můžeme lehce přimíchat i další textové signály z case
    for key in ("domain", "intent", "notes"):
        val = case.get(key)
        if isinstance(val, str):
            extra_context_pieces.append(val)

    full_text = _normalize_text(" ".join([user_query] + extra_context_pieces))

    flags = _collect_flags(full_text, case)
    base_score = sum(int(f.get("weight", 1)) for f in flags)
    dimensions = _aggregate_dimensions(flags)

    # úprava podle intent/domain
    score = _adjust_score(base_score, dimensions, intent, domain)
    level = _score_to_level(score)

    # volitelný LLM hook – pokud je v contextu use_llm=True
    use_llm = bool(ctx.get("use_llm"))
    llm_risk: Dict[str, Any] = {}
    if use_llm:
        llm_risk = _llm_risk_analysis(case)

    payload: Dict[str, Any] = {
        "level": level,             # LOW / MEDIUM / HIGH
        "score": score,             # upravený součet vah
        "flags": flags,             # detailní seznam signálů
        "dimensions": dimensions,   # agregace podle dimenzí
        "intent": intent,
        "domain": domain,
        "base_score": base_score,   # pro debug – původní skóre bez úprav
    }

    if llm_risk:
        payload["llm_risk"] = llm_risk

    notes: List[str] = [
        f"risk_engine: level={level}, score={score}, base_score={base_score}",
        "Heuristický model v2: kombinace klíčových slov, dimenzí rizika, intentu a domény.",
        "LLM hook aktivní" if llm_risk else "LLM hook neaktivní nebo bez výstupu.",
    ]

    return EngineOutput(
        name="risk_engine",
        payload=payload,
        notes=notes,
    )