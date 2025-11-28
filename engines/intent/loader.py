# engines/intent/loader.py
from __future__ import annotations

import os
import json
from typing import List

from .definition import IntentDefinition  # dataclass pro JSON intent definice

# kořenový adresář s intent JSONy
BASE_DIR = os.path.join("data", "intents")


def load_intents() -> List[IntentDefinition]:
    """
    Načte všechny intent definice z data/intents/**.
    Očekává JSON ve formátu kompatibilním s IntentDefinition.
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

                # zpětná kompatibilita: starší JSONy mají klíč "id"
                if "id" in raw and "intent_id" not in raw:
                    raw["intent_id"] = raw.pop("id")

                results.append(IntentDefinition(**raw))
            except Exception as e:
                # záměrně jen logujeme, aby jediný rozbitý soubor neshodil celý engine
                print(f"[intent_loader] Error loading {full_path}: {e}")

    return results


# re-export pro pohodlný import
__all__ = ["load_intents", "IntentDefinition"]