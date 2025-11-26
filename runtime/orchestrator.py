"""
Orchestrátor právního agenta (v1)

Zatím:
- spustí Core Legal Engine (IRAC, skeleton/LLM)
- spustí Risk Engine (deadline/trestní/děti/…)
- složí z toho finální markdown odpověď pro uživatele

Později:
- přidáme judikaturu, procedurální doporučení, napojení na frontend atd.
"""

from __future__ import annotations

from typing import Any, Dict, List

from engines.shared_types import EngineInput
from engines.core_legal.engine import run as run_core_legal
from engines.risk.engine import run as run_risk


def _safe_get_first(list_value: Any, key: str) -> str:
    """
    Pomocná funkce: vezme první prvek seznamu slovníků a vrátí hodnotu pod `key`.
    Pokud cokoliv chybí, vrátí rozumný skeleton text.
    """
    if not isinstance(list_value, list) or not list_value:
        return "(zatím prázdné – skeleton verze)"
    item = list_value[0]
    if not isinstance(item, dict):
        return "(zatím prázdné – skeleton verze)"
    return str(item.get(key, "(zatím prázdné – skeleton verze)"))


def _render_risk_section(risk_payload: Dict[str, Any]) -> str:
    level = risk_payload.get("level", "LOW")
    score = risk_payload.get("score", 0)
    flags: List[Dict[str, Any]] = risk_payload.get("flags", []) or []

    lines: List[str] = []
    lines.append(f"- Úroveň rizika: **{level}** (score: {score})")

    if not flags:
        lines.append("- Nebyla detekována žádná specifická riziková oblast.")
        return "\n".join(lines)

    lines.append("- Detekované rizikové oblasti:")

    for f in flags:
        name = f.get("flag", "unknown_flag")
        weight = f.get("weight", "?")
        hits = f.get("keywords_hit", []) or []
        hits_str = ", ".join(str(h) for h in hits)
        lines.append(f"  - `{name}` (váha {weight}) – klíčová slova: {hits_str}")

    return "\n".join(lines)


def run_pipeline(user_query: str) -> Dict[str, Any]:
    """
    Hlavní vstupní bod pro backend / API.

    Vrací slovník:
    {
        "final_answer": <markdown string>,
        "core_legal": <EngineOutput>,
        "risk": <EngineOutput>,
    }
    """
    engine_input = EngineInput(context={"case": {"user_query": user_query}})

    # 1) Core právní analýza
    core_legal_out = run_core_legal(engine_input)
    core_payload = core_legal_out.payload or {}

    issues_text = _safe_get_first(core_payload.get("issues"), "text")
    rules_text = _safe_get_first(core_payload.get("rules"), "text")
    analysis_text = _safe_get_first(core_payload.get("analysis"), "text")
    conclusion = core_payload.get("conclusion", {}) or {}
    conclusion_text = str(conclusion.get("summary", "(zatím bez závěru)"))

    # 2) Risk / safety analýza
    risk_out = run_risk(engine_input)
    risk_payload = risk_out.payload or {}
    risk_section = _render_risk_section(risk_payload)

    # 3) Složení finální odpovědi – skeleton layout pro veřejnost
    final_answer = f"""# 🧩 Shrnutí

Skeleton verze: shrnutí bude v plné verzi generováno na základě kombinace
právní analýzy (Core Legal Engine) a risk/safety vrstvy. Teď slouží hlavně
k ověření architektury a struktury výstupu.

---

## ⚖️ Právní analýza

### Hlavní právní otázka
{issues_text}

### Relevantní právní úprava
{rules_text}

### Analýza situace
{analysis_text}

### Předběžný závěr
{conclusion_text}

---

## 📚 Judikatura

V této skeleton verzi ještě není implementováno vyhledávání judikatury.
V budoucnu zde budou přímé odkazy na rozhodnutí soudů, která se týkají
podobných situací.

---

## ⚠️ Rizika a naléhavost

{risk_section}

---

## 🧭 Doporučený další postup

Skeleton verze: v plné verzi zde budou konkrétní doporučené kroky
(co může uživatel udělat sám, kdy má zvážit advokáta, jaké lhůty hlídat, atd.).
Aktuálně je cílem hlavně ověřit, že orchestrátor správně skládá informace
z Core Legal Engine a Risk Engine do jednoho výstupu.

"""

    return {
        "final_answer": final_answer,
        "core_legal": core_legal_out,
        "risk": risk_out,
    }