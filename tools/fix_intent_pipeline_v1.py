#!/usr/bin/env python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from datetime import datetime, timezone


REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = REPO_ROOT / "data" / "_source" / "domains" / "traffic_law" / "intents"
TARGET_DIR = REPO_ROOT / "data" / "intents" / "traffic_law"


def _header() -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return (
        "Run type : FIX\n"
        f"Timestamp (UTC) : {now}\n"
        "Task : Automatický bootstrap intentů pro traffic_law + sanity test\n"
        "------------------------------------------------------------------------\n"
    )


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _write_file(path: Path, content: str) -> None:
    _ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8")


def _create_bootstrap_script() -> Path:
    path = REPO_ROOT / "tools" / "bootstrap_traffic_law_intents.py"
    content = r'''#!/usr/bin/env python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from engines.intent.loader import _normalize_raw
from engines.intent.definition import IntentDefinition


REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = REPO_ROOT / "data" / "_source" / "domains" / "traffic_law" / "intents"
TARGET_DIR = REPO_ROOT / "data" / "intents" / "traffic_law"


def _ensure_runtime_dir() -> None:
    TARGET_DIR.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _normalize_source_intent(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Připraví raw JSON ze _source tak, aby odpovídal IntentDefinition.
    Použije _normalize_raw + vynutí domain a intent_id.
    """
    # traffic_law jako doména
    raw["domain"] = "traffic_law"

    # fallback: pokud chybí id/intent_id, použijeme filename na call-site
    normalized = _normalize_raw(raw)

    # validace proti dataclass – ať spadne tady, ne až v runtime
    IntentDefinition(**normalized)
    return normalized


def bootstrap_traffic_law_intents() -> None:
    """
    Vygeneruje data/intents/traffic_law/*.json z _source definic.
    Idempotentní – stejné soubory přepisuje.
    """
    _ensure_runtime_dir()

    for path in sorted(SOURCE_DIR.glob("*.json")):
        raw = _load_json(path)

        # fallback pro intent_id z názvu souboru, pokud by chybělo
        if "intent_id" not in raw and "id" not in raw:
            stem = path.stem
            raw["intent_id"] = stem

        # doména traffic_law
        raw["domain"] = "traffic_law"

        normalized = _normalize_source_intent(raw)

        target_path = TARGET_DIR / path.name
        with target_path.open("w", encoding="utf-8") as f:
            json.dump(normalized, f, ensure_ascii=False, indent=2)

        print(f"[bootstrap_traffic_law_intents] wrote {target_path}")


if __name__ == "__main__":
    bootstrap_traffic_law_intents()
'''
    _write_file(path, content)
    return path


def _create_test_file() -> Path:
    path = REPO_ROOT / "tests" / "test_intent_loader_runtime_minimal.py"
    content = r'''from __future__ import annotations

from engines.intent.loader import load_intents


def test_load_intents_returns_non_empty_list() -> None:
    """
    Sanity check: loader by měl načíst alespoň jeden intent z data/intents.
    Před spuštěním testů je vhodné spustit:
        python tools/bootstrap_traffic_law_intents.py
    """
    intents = load_intents()
    assert isinstance(intents, list)
    assert len(intents) > 0
'''
    _write_file(path, content)
    return path


def _bootstrap_runtime_intents(bootstrap_script: Path) -> str:
    """
    Spustí bootstrap script v rámci stejného repa (přes python -m).
    Použijeme exec() kvůli jednoduchosti – běží to jen v CI.
    """
    import runpy

    before = sorted(TARGET_DIR.glob("*.json")) if TARGET_DIR.exists() else []
    runpy.run_path(str(bootstrap_script))
    after = sorted(TARGET_DIR.glob("*.json")) if TARGET_DIR.exists() else []

    created = [p for p in after if p not in before]
    return ", ".join(p.name for p in created) if created else "(žádné nové, jen přepsáno)"


def main() -> None:
    parts = []
    parts.append(_header())

    # 1) Bootstrap script
    bootstrap_path = _create_bootstrap_script()
    parts.append(f"Vytvořen/aktualizován: {bootstrap_path.relative_to(REPO_ROOT)}")

    # 2) Test file
    test_path = _create_test_file()
    parts.append(f"Vytvořen/aktualizován: {test_path.relative_to(REPO_ROOT)}")

    # 3) Bootstrap runtime intentů
    _ensure_dir(TARGET_DIR)
    created = _bootstrap_runtime_intents(bootstrap_path)
    parts.append(f"Vygenerované/aktualizované runtime intenty v data/intents/traffic_law: {created}")

    report = "\n".join(parts)
    print(report)


if __name__ == "__main__":
    main()
