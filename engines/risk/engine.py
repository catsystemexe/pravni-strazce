"""
Risk / Safety Engine v1

- analyzuje text dotazu (user_query)
- hledá rizikové oblasti podle klíčových slov
- vrací celkový risk_level (LOW / MEDIUM / HIGH)
- + seznam nalezených flags
"""

from __future__ import annotations

from typing import Any, Dict, List

from ..shared_types import EngineInput, EngineOutput
from runtime.config_loader import load_yaml

_CONFIG = load_yaml("engines/risk/config.yaml")


def _compute_risk_score(text: str) -> Dict[str, Any]:
    text_lower = text.lower()
    flags_cfg = _CONFIG.get("flags", {}) or {}

    total_score = 0
    matched_flags: List[Dict[str, Any]] = []

    for flag_name, cfg in flags_cfg.items():
        keywords = cfg.get("keywords", []) or []
        weight = int(cfg.get("weight", 1))

        hits = []
        for kw in keywords:
            if kw.lower() in text_lower:
                hits.append(kw)

        if hits:
            total_score += weight
            matched_flags.append(
                {
                    "flag": flag_name,
                    "weight": weight,
                    "keywords_hit": hits,
                }
            )

    # Určení úrovně rizika
    levels = _CONFIG.get("levels", {}) or {}
    level_name = "LOW"
    for name, lf in levels.items():
        if lf.get("score_min", 0) <= total_score <= lf.get("score_max", 999):
            level_name = name
            break

    return {
        "score": total_score,
        "level": level_name,
        "flags": matched_flags,
    }


def run(engine_input: EngineInput) -> EngineOutput:
    """
    Hlavní entry point risk engine.

    Čte:
    - engine_input.context["case"]["user_query"]
      (pokud chybí, risk je LOW a prázdné flags)
    """
    case = engine_input.context.get("case", {}) or {}
    user_query = case.get("user_query") or ""

    if not user_query.strip():
        payload = {
            "level": "LOW",
            "score": 0,
            "flags": [],
            "message": "Chybí text dotazu, nelze odhadnout rizikovost.",
        }
        return EngineOutput(
            name="risk_engine",
            payload=payload,
            notes=["risk_engine: empty user_query -> LOW"],
        )

    res = _compute_risk_score(user_query)

    payload = {
        "level": res["level"],
        "score": res["score"],
        "flags": res["flags"],
    }

    notes = [
        f"risk_engine: level={res['level']} score={res['score']} flags={len(res['flags'])}",
    ]

    return EngineOutput(
        name="risk_engine",
        payload=payload,
        notes=notes,
    )
