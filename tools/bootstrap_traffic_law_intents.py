#!/usr/bin/env python3
"""
Jednoduchý bootstrap pro traffic_law:
- vezme všechny JSON soubory v
    data/_source/domains/traffic_law/intents/*.json
- doplní jim:
    - intent_id (pokud chybí) z názvu souboru
    - domain = "traffic_law" (přepíše / doplní)
- uloží je do:
    data/intents/traffic_law/<stejné_jméno>.json

Bez importu z `engines.*` – je to čistý datový kopírovací krok.
"""
print("BOOTSTRAP_VERSION = traffic_law_v3_no_engines")


from pathlib import Path
import json
from typing import Any, Dict


# Kořen projektu: .../pravni-strazce/pravni-strazce
PROJECT_ROOT = Path(__file__).resolve().parents[1]

SOURCE_DIR = PROJECT_ROOT / "data" / "_source" / "domains" / "traffic_law" / "intents"
TARGET_DIR = PROJECT_ROOT / "data" / "intents" / "traffic_law"


def _ensure_target_dir() -> None:
    TARGET_DIR.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _prepare_intent(raw: Dict[str, Any], filename_stem: str) -> Dict[str, Any]:
    """
    Minimální příprava runtime intentu:
    - doplní intent_id, pokud chybí
    - nastaví domain = "traffic_law"
    Ostatní pole nechává tak, jak jsou v _source.
    """
    if "intent_id" not in raw and "id" not in raw:
        raw["intent_id"] = filename_stem
    elif "id" in raw and "intent_id" not in raw:
        # sjednocení staršího klíče
        raw["intent_id"] = raw["id"]

    # pevná doména pro tento bootstrap
    raw["domain"] = "traffic_law"

    return raw


def bootstrap_traffic_law_intents() -> int:
    """
    Vygeneruje data/intents/traffic_law/*.json z
    data/_source/domains/traffic_law/intents/*.json.
    Je idempotentní – opakované spuštění jen přepíše existující soubory.
    """
    _ensure_target_dir()

    if not SOURCE_DIR.exists():
        print(f"[bootstrap_traffic_law_intents] SOURCE_DIR not found: {SOURCE_DIR}")
        return 0

    count = 0
    for path in sorted(SOURCE_DIR.glob("*.json")):
        raw = _load_json(path)
        prepared = _prepare_intent(raw, path.stem)

        target_path = TARGET_DIR / path.name
        with target_path.open("w", encoding="utf-8") as f:
            json.dump(prepared, f, ensure_ascii=False, indent=2)

        print(f"[bootstrap_traffic_law_intents] wrote {target_path}")
        count += 1

    print(f"[bootstrap_traffic_law_intents] total intents: {count}")
    return count


def main() -> None:
    bootstrap_traffic_law_intents()


if __name__ == "__main__":
    main()
