# engines/intent/loader.py
from __future__ import annotations

import os
import json
from typing import List, Dict, Any

from .definition import IntentDefinition


BASE_DIR = os.path.join("data", "intents")


def _normalize_raw(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalizuje JSON tak, aby odpovídal IntentDefinition dataclass.
    - id -> intent_id
    - přidá missing keywords / negative_keywords
    - odstraní klíče, které dataclass nezná
    """

    raw = dict(raw)  # shallow copy

    # --- přejmenování id → intent_id ---
    if "id" in raw and "intent_id" not in raw:
        raw["intent_id"] = raw.pop("id")

    # --- keywords / negative_keywords povinné ---
    if "keywords" not in raw:
        raw["keywords"] = []
    if "negative_keywords" not in raw:
        raw["negative_keywords"] = []

    # --- intent_group (pokud nechceš, dataclass ho nemá mít) ---
    if "intent_group" in raw:
        raw.pop("intent_group")

    # --- whitelist validních položek podle IntentDefinition ---
    valid_fields = {
        "intent_id",
        "label_cs",
        "domain",
        "subdomains",
        "description_cs",
        "keywords",
        "negative_keywords",
        "risk_patterns",
        "basic_questions",
        "safety_questions",
        "normative_references",
        "conclusion_skeletons",
        "notes",
        "version",
    }

    # odfiltruje klíče, které dataclass nezná (jinak selže **raw → IntentDefinition**)
    for k in list(raw.keys()):
        if k not in valid_fields:
            raw.pop(k)

    return raw


def load_intents() -> List[IntentDefinition]:
    """
    Načte všechny intent definice z data/intents/**.
    Bezpečné: chybný JSON neshodí celý engine.
    """
    results: List[IntentDefinition] = []

    for root, dirs, files in os.walk(BASE_DIR):
        for fname in files:
            if not fname.endswith(".json"):
                continue

            full_path = os.path.join(root, fname)

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)

                normalized = _normalize_raw(raw)
                intent = IntentDefinition(**normalized)
                results.append(intent)

            except Exception as e:
                print(f"[intent_loader] Error loading {full_path}: {e}")

    return results


__all__ = ["load_intents", "IntentDefinition"]