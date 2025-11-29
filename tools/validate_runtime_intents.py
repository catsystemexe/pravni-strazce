#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Kořen repozitáře = parent adresář tools/
REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = REPO_ROOT / "data" / "intents"

# Upravit podle reálného IntentDefinition, pokud máš jinak pojmenovaná pole
REQUIRED_FIELDS = [
    "intent_id",
    "label_cs",
    "domain",
    "description_cs",
    "subdomains",
    "keywords",
    "negative_keywords",
    "risk_patterns",
    "basic_questions",
    "safety_questions",
    "normative_references",
    "conclusion_skeletons",
]

OPTIONAL_FIELDS = [
    "notes",
    "version",
    "intent_group",
    "examples",
]


def _type_name(x: Any) -> str:
    return type(x).__name__


def validate_file(path: Path, domain_from_dir: str) -> Tuple[List[str], str | None]:
    errors: List[str] = []
    intent_id: str | None = None

    # 1) JSON syntax
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except Exception as e:  # noqa: BLE001
        errors.append(f"{path}: JSON parse error: {e}")
        return errors, None

    if not isinstance(data, dict):
        errors.append(f"{path}: root must be JSON object, got {_type_name(data)}")
        return errors, None

    # 2) Povinná pole
    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"{path}: missing required field '{field}'")

    if errors:
        return errors, None  # dál nemá cenu pokračovat

    # 3) Typy základních polí
    def expect_type(field: str, expected_type, allow_none: bool = False):
        value = data.get(field)
        if value is None and allow_none:
            return
        if not isinstance(value, expected_type):
            errors.append(
                f"{path}: field '{field}' must be {expected_type.__name__}, "
                f"got {_type_name(value)}"
            )

    for fld in ["intent_id", "label_cs", "domain", "description_cs"]:
        expect_type(fld, str)

    for fld in [
        "subdomains",
        "keywords",
        "negative_keywords",
        "basic_questions",
        "safety_questions",
        "normative_references",
    ]:
        expect_type(fld, list)
        if isinstance(data.get(fld), list):
            for i, item in enumerate(data[fld]):
                if not isinstance(item, str):
                    errors.append(
                        f"{path}: field '{fld}[{i}]' must be str, got {_type_name(item)}"
                    )

    expect_type("risk_patterns", list)
    expect_type("conclusion_skeletons", dict)

    for fld in ["notes", "version", "intent_group"]:
        if fld in data:
            expect_type(fld, str, allow_none=False)

    if "examples" in data:
        expect_type("examples", list)
        if isinstance(data.get("examples"), list):
            for i, ex in enumerate(data["examples"]):
                if not isinstance(ex, str):
                    errors.append(
                        f"{path}: field 'examples[{i}]' must be str, got {_type_name(ex)}"
                    )

    # 4) Konzistence domain vs adresář
    domain = data.get("domain")
    if domain != domain_from_dir:
        errors.append(
            f"{path}: domain mismatch – JSON has '{domain}', "
            f"directory is '{domain_from_dir}'"
        )

    # 5) Základní obsahové sanity checky
    if not data["label_cs"].strip():
        errors.append(f"{path}: label_cs is empty")

    if not data["description_cs"].strip():
        errors.append(f"{path}: description_cs is empty")

    keywords = data.get("keywords") or []
    if isinstance(keywords, list) and len(keywords) < 3:
        errors.append(
            f"{path}: keywords should contain at least 3 items (found {len(keywords)})"
        )

    intent_id = data.get("intent_id")
    if isinstance(intent_id, str):
        if not intent_id.strip():
            errors.append(f"{path}: intent_id is empty")
        # jednoduché doporučení – můžeš změnit/zakomentovat
        if not intent_id.startswith(domain_from_dir + "_"):
            errors.append(
                f"{path}: intent_id '{intent_id}' should start with "
                f"domain prefix '{domain_from_dir}_' (recommendation)"
            )

    # 6) lehká sanity pro conclusion_skeletons – aspoň nějaký klíč
    concl = data.get("conclusion_skeletons") or {}
    if isinstance(concl, dict) and not concl:
        errors.append(f"{path}: conclusion_skeletons is empty dict")

    return errors, intent_id


def main() -> int:
    if not RUNTIME_DIR.exists():
        print(f"[ERROR] Runtime intents dir does not exist: {RUNTIME_DIR}", file=sys.stderr)
        return 1

    all_errors: List[str] = []
    seen_intent_ids: Dict[str, Path] = {}

    for domain_dir in sorted(RUNTIME_DIR.iterdir()):
        if not domain_dir.is_dir():
            continue
        domain_name = domain_dir.name

        for json_path in sorted(domain_dir.glob("*.json")):
            errors, intent_id = validate_file(json_path, domain_name)
            all_errors.extend(errors)

            if intent_id:
                if intent_id in seen_intent_ids:
                    prev = seen_intent_ids[intent_id]
                    all_errors.append(
                        f"Duplicate intent_id '{intent_id}' in "
                        f"{json_path} and {prev}"
                    )
                else:
                    seen_intent_ids[intent_id] = json_path

    if all_errors:
    if all_errors:
        print("========================================")
        print("RUNTIME INTENTS VALIDATION – ERRORS FOUND")
        print("========================================")
        for err in all_errors:
            print(f"- {err}")
        print()
        print(f"Total errors: {len(all_errors)}")
        return 1

    print("========================================")
    print("RUNTIME INTENTS VALIDATION – OK")
    print("========================================")
    print(f"Checked {len(seen_intent_ids)} intents in {RUNTIME_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
    
        
