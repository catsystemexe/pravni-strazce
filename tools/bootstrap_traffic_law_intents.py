#!/usr/bin/env python3

import sys
from pathlib import Path
import json
from typing import Any, Dict

# --- zajisti, že se najde balíček "engines" i při běhu z GitHub Actions ---
ROOT = Path(__file__).resolve().parents[1]  # .../pravni-strazce/pravni-strazce
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.intent.loader import _normalize_raw
from engines.intent.definition import IntentDefinition

SOURCE_DIR = ROOT / "data" / "_source" / "domains" / "traffic_law" / "intents"
TARGET_DIR = ROOT / "data" / "intents" / "traffic_law"


def _ensure_target_dir() -> None:
    TARGET_DIR.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _normalize_source_intent(raw: Dict[str, Any], filename_stem: str) -> Dict[str, Any]:
    """
    Připraví raw JSON ze _source tak, aby odpovídal IntentDefinition:
    - doplní intent_id z názvu souboru, pokud chybí
    - nastaví domain = "traffic_law"
    - projede _normalize_raw z loaderu
    - ověří validitu přes IntentDefinition(**normalized)
    """
    if "intent_id" not in raw and "id" not in raw:
        raw["intent_id"] = filename_stem

    # traffic_law je pro tyhle intenty pevná doména
    raw["domain"] = "traffic_law"

    normalized = _normalize_raw(raw)
    # validace – případné chyby chceme vidět hned při bootstrapu
    IntentDefinition(**normalized)
    return normalized


def bootstrap_traffic_law_intents() -> int:
    """
    Vygeneruje data/intents/traffic_law/*.json z data/_source/domains/traffic_law/intents/*.json.
    Je idempotentní – opakované spuštění jen přepíše existující soubory.
    """
    _ensure_target_dir()

    if not SOURCE_DIR.exists():
        print(f"[bootstrap_traffic_law_intents] SOURCE_DIR not found: {SOURCE_DIR}")
        return 0

    count = 0
    for path in sorted(SOURCE_DIR.glob("*.json")):
        raw = _load_json(path)
        normalized = _normalize_source_intent(raw, path.stem)

        target_path = TARGET_DIR / path.name
        with target_path.open("w", encoding="utf-8") as f:
            json.dump(normalized, f, ensure_ascii=False, indent=2)

        print(f"[bootstrap_traffic_law_intents] wrote {target_path}")
        count += 1

    print(f"[bootstrap_traffic_law_intents] total intents: {count}")
    return count


def main() -> None:
    bootstrap_traffic_law_intents()


if __name__ == "__main__":
    main()
