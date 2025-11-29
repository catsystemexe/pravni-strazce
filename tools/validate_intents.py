# tools/validate_intents.py
from __future__ import annotations

import json
import os
import re
import sys
from typing import Any, Dict, List, Tuple

from engines.intent.definition import IntentDefinition  # dataclass pro JSON intent definice

from pathlib import Path

DATA_ROOT = Path("data")
YAML_DOMAINS_ROOT = DATA_ROOT / "_source" / "domains"   # zdrojové YAML
JSON_INTENTS_ROOT = DATA_ROOT / "intents"               # runtime JSON

BASE_DIR = os.path.join("data", "intents")

# --------- konfig validačních pravidel ----------

REQUIRED_FIELDS = [
    "intent_id",
    "label_cs",
    "domain",
    "subdomains",
    "description_cs",
    "keywords",
    "negative_keywords",
    "basic_questions",
    "safety_questions",
    "risk_patterns",
    "normative_references",
    "conclusion_skeletons",
    "version",
]

EXPECTED_TYPES = {
    "intent_id": str,
    "label_cs": str,
    "domain": str,
    "subdomains": list,
    "description_cs": str,
    "keywords": list,
    "negative_keywords": list,
    "basic_questions": list,
    "safety_questions": list,
    "risk_patterns": list,
    "normative_references": list,
    "conclusion_skeletons": dict,
    "version": str,
}

REQUIRED_SKELETON_KEYS = {"low", "medium", "high"}

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
SNAKE_RE = re.compile(r"^[a-z0-9_]+$")


# --------- pomocné funkce ----------

def iter_intent_files() -> List[str]:
    paths: List[str] = []
    for root, dirs, files in os.walk(BASE_DIR):
        for fname in files:
            if fname.endswith(".json"):
                paths.append(os.path.join(root, fname))
    paths.sort()
    return paths


def _short(path: str) -> str:
    # hezčí relativní cesta do výpisu
    return os.path.relpath(path, BASE_DIR)


def validate_style(
    rel: str,
    raw: Dict[str, Any],
) -> Tuple[int, int]:
    """
    „Měkké“ lint kontroly:
      - label_cs: velké písmeno, bez tečky na konci
      - intent_id, domain, subdomains: snake_case
      - version: semver X.Y.Z
      - basic/safety_questions končí otazníkem
      - description_cs není úplná blbost (min. délka)
    Vrací (errors, warnings).
    """
    errors = 0
    warnings = 0

    # label_cs
    label = raw.get("label_cs")
    if isinstance(label, str):
        stripped = label.strip()
        if not stripped:
            print(f"[ERROR] {rel}: label_cs je prázdný")
            errors += 1
        else:
            if not stripped[0].isupper():
                print(f"[WARN ] {rel}: label_cs nezačíná velkým písmenem: '{label}'")
                warnings += 1
            if stripped.endswith("."):
                print(f"[WARN ] {rel}: label_cs končí tečkou – není potřeba: '{label}'")
                warnings += 1

    # intent_id, domain, subdomains – snake_case
    for field in ("intent_id", "domain"):
        val = raw.get(field)
        if isinstance(val, str):
            if not SNAKE_RE.match(val):
                print(
                    f"[WARN ] {rel}: '{field}' není čisté snake_case "
                    f"(a-z0-9_): '{val}'"
                )
                warnings += 1

    subdomains = raw.get("subdomains", [])
    if isinstance(subdomains, list):
        for i, sd in enumerate(subdomains):
            if isinstance(sd, str) and not SNAKE_RE.match(sd):
                print(
                    f"[WARN ] {rel}: subdomains[{i}] není snake_case: '{sd}'"
                )
                warnings += 1

    # version – semver X.Y.Z
    version = raw.get("version")
    if isinstance(version, str):
        if not SEMVER_RE.match(version.strip()):
            print(
                f"[WARN ] {rel}: version '{version}' není ve formátu X.Y.Z "
                "(např. 1.0.0)"
            )
            warnings += 1

    # description_cs – aspoň nějaká délka
    desc = raw.get("description_cs")
    if isinstance(desc, str):
        if len(desc.strip()) < 20:
            print(
                f"[WARN ] {rel}: description_cs je velmi krátký "
                f"({len(desc.strip())} znaků) – zvaž rozšíření."
            )
            warnings += 1

    # otázky – měly by končit '?' a nebýt prázdné
    for field in ("basic_questions", "safety_questions"):
        q_list = raw.get(field, [])
        if not isinstance(q_list, list):
            continue
        if len(q_list) == 0:
            print(f"[WARN ] {rel}: pole '{field}' je prázdné – "
                  "zvaž přidání aspoň několika otázek.")
            warnings += 1
            continue
        for i, q in enumerate(q_list):
            if not isinstance(q, str):
                continue
            qt = q.strip()
            if not qt:
                print(f"[WARN ] {rel}: {field}[{i}] je prázdný řetězec")
                warnings += 1
            elif not qt.endswith("?"):
                print(
                    f"[WARN ] {rel}: {field}[{i}] nekončí otazníkem: '{qt}'"
                )
                warnings += 1

    return errors, warnings


def validate_single_file(
    path: str,
    seen_ids: Dict[str, str],
    keyword_index: Dict[str, List[str]],
) -> Tuple[bool, int, int]:
    """
    Vrací (ok, errors_count, warnings_count)
    """
    errors = 0
    warnings = 0
    rel = _short(path)

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw: Dict[str, Any] = json.load(f)
    except Exception as e:
        print(f"[ERROR] {rel}: nelze načíst JSON: {e}")
        return False, 1, 0

    # 1) pokus o vytvoření IntentDefinition – chytí hrubé typové chyby
    try:
        intent = IntentDefinition(**raw)
    except Exception as e:
        print(f"[ERROR] {rel}: IntentDefinition(**raw) selhalo: {e}")
        return False, 1, 0

    # 2) povinná pole
    for field in REQUIRED_FIELDS:
        if field not in raw:
            print(f"[ERROR] {rel}: chybí povinné pole '{field}'")
            errors += 1

    # 3) typová kontrola základních polí
    for field, expected_type in EXPECTED_TYPES.items():
        if field not in raw:
            continue
        value = raw[field]
        if not isinstance(value, expected_type):
            print(
                f"[ERROR] {rel}: pole '{field}' má typ {type(value).__name__}, "
                f"očekáván {expected_type.__name__}"
            )
            errors += 1

    # 4) detaily pro některé struktury
    # subdomains – list[str]
    subdomains = raw.get("subdomains", [])
    if isinstance(subdomains, list):
        for i, sd in enumerate(subdomains):
            if not isinstance(sd, str):
                print(f"[ERROR] {rel}: subdomains[{i}] není str")
                errors += 1

    # keywords / negative_keywords – list[str]
    for field in ("keywords", "negative_keywords"):
        val = raw.get(field, [])
        if isinstance(val, list):
            for i, kw in enumerate(val):
                if not isinstance(kw, str):
                    print(f"[ERROR] {rel}: {field}[{i}] není str")
                    errors += 1
        # lehké doporučení – příliš málo klíčových slov
        if field == "keywords" and isinstance(val, list) and len(val) < 3:
            print(f"[WARN ] {rel}: pole 'keywords' má jen {len(val)} položky (doporučeno ≥ 3)")
            warnings += 1

    # risk_patterns – list[dict]
    risk_patterns = raw.get("risk_patterns", [])
    if isinstance(risk_patterns, list):
        for i, rp in enumerate(risk_patterns):
            if not isinstance(rp, dict):
                print(f"[ERROR] {rel}: risk_patterns[{i}] není dict")
                errors += 1
                continue
            if "pattern" not in rp:
                print(f"[ERROR] {rel}: risk_patterns[{i}] nemá klíč 'pattern'")
                errors += 1

    # conclusion_skeletons – musí mít low/medium/high
    cs = raw.get("conclusion_skeletons", {})
    if isinstance(cs, dict):
        missing = REQUIRED_SKELETON_KEYS - set(cs.keys())
        if missing:
            print(
                f"[ERROR] {rel}: conclusion_skeletons chybí klíče: {', '.join(sorted(missing))}"
            )
            errors += 1

    # 5) unikátnost intent_id
    intent_id = raw.get("intent_id")
    if isinstance(intent_id, str):
        if intent_id in seen_ids:
            print(
                f"[ERROR] {rel}: duplicitní intent_id '{intent_id}' "
                f"(už použito v {_short(seen_ids[intent_id])})"
            )
            errors += 1
        else:
            seen_ids[intent_id] = path

    # 6) indexace keywords pro kolize
    kws = raw.get("keywords", [])
    if isinstance(kws, list):
        for kw in kws:
            if not isinstance(kw, str):
                continue
            kw_norm = kw.strip().lower()
            if not kw_norm:
                continue
            keyword_index.setdefault(kw_norm, []).append(intent_id or rel)

    # 7) stylistické/lint kontroly
    s_err, s_warn = validate_style(rel, raw)
    errors += s_err
    warnings += s_warn

    return errors == 0, errors, warnings


def main() -> None:
    print("== Validace intent definic z data/intents ==")

    files = iter_intent_files()
    if not files:
        print("[WARN ] Nenašly se žádné JSON soubory v data/intents")
        sys.exit(0)

    seen_ids: Dict[str, str] = {}
    keyword_index: Dict[str, List[str]] = {}

    total_errors = 0
    total_warnings = 0

    for path in files:
        ok, e_cnt, w_cnt = validate_single_file(path, seen_ids, keyword_index)
        total_errors += e_cnt
        total_warnings += w_cnt

    # 8) detekce kolizí klíčových slov (stejné keyword ve více intentech)
    collisions = {
        kw: ids for kw, ids in keyword_index.items() if len(ids) > 1
    }
    if collisions:
        print("\n[INFO ] Detekované kolize klíčových slov (může, ale nemusí být problém):")
        for kw, ids in sorted(collisions.items()):
            joined = ", ".join(sorted(set(ids)))
            print(f"  - '{kw}': {joined}")

    print("\n== Shrnutí ==")
    print(f"Errors  : {total_errors}")
    print(f"Warnings: {total_warnings}")

    if total_errors > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()