from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Set

from runtime.config_loader import BASE_DIR
from runtime.domain_catalog import load_domains, list_domain_ids


DATA_DIR = BASE_DIR / "data"
INTENTS_DIR = DATA_DIR / "intents"


REQUIRED_INTENT_KEYS = {
    "intent_id",
    "label_cs",
    "domain",
    "subdomains",
    "description_cs",
    "risk_patterns",
    "basic_questions",
    "safety_questions",
    "normative_references",
    "conclusion_skeletons",
}


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_intent_file(path: Path, domain_ids: Set[str], domain_subdomains_map: Dict[str, Set[str]]) -> List[str]:
    errors: List[str] = []
    rel = path.relative_to(DATA_DIR)

    try:
        data = _load_json(path)
    except Exception as e:
        errors.append(f"{rel}: JSON load error: {e}")
        return errors

    # 1) required keys
    missing = REQUIRED_INTENT_KEYS - set(data.keys())
    if missing:
        errors.append(f"{rel}: missing keys: {sorted(missing)}")

    domain = data.get("domain")
    if not isinstance(domain, str):
        errors.append(f"{rel}: 'domain' must be string")
    elif domain not in domain_ids:
        errors.append(f"{rel}: 'domain' '{domain}' not found in domains.json")

    # subdomains sanity
    subdomains = data.get("subdomains", [])
    if not isinstance(subdomains, list):
        errors.append(f"{rel}: 'subdomains' must be list")
    else:
        if domain in domain_subdomains_map:
            allowed = domain_subdomains_map[domain]
            for sd in subdomains:
                if sd not in allowed:
                    errors.append(f"{rel}: subdomain '{sd}' not declared in domains.json for domain '{domain}'")

    # conclusion_skeletons shape
    concl = data.get("conclusion_skeletons", {})
    if not isinstance(concl, dict):
        errors.append(f"{rel}: 'conclusion_skeletons' must be dict")
    else:
        for level in ("low", "medium", "high"):
            if level not in concl:
                errors.append(f"{rel}: 'conclusion_skeletons' missing key '{level}'")

    return errors


def build_domain_subdomains_map() -> Dict[str, Set[str]]:
    mapping: Dict[str, Set[str]] = {}
    doms = load_domains()
    for d in doms.get("domains", []):
        did = d.get("id")
        subs = d.get("subdomains", [])
        if isinstance(did, str):
            mapping[did] = set(s for s in subs if isinstance(s, str))
    return mapping


def main() -> None:
    domain_ids = set(list_domain_ids())
    domain_subs = build_domain_subdomains_map()

    all_errors: List[str] = []

    if not INTENTS_DIR.exists():
        print("No data/intents directory, nothing to validate.")
        return

    for domain_dir in sorted(INTENTS_DIR.iterdir()):
        if not domain_dir.is_dir():
            continue
        if domain_dir.name.startswith("_"):
            continue

        for path in sorted(domain_dir.glob("*.json")):
            errors = validate_intent_file(path, domain_ids, domain_subs)
            all_errors.extend(errors)

    if not all_errors:
        print("✅ Data validation OK – all intents match domains.json and schema.")
    else:
        print("❌ Data validation found issues:")
        for e in all_errors:
            print(" -", e)


if __name__ == "__main__":
    main()