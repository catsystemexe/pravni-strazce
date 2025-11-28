from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from runtime.config_loader import BASE_DIR

_DATA_DIR = BASE_DIR / "data"
_SCHEMA_DIR = _DATA_DIR / "schema"
_INTENTS_DIR = _DATA_DIR / "intents"


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_domains() -> Dict[str, Any]:
    """Načte domains.json a vrátí dict s klíči:
    - catalog_name, version, domains (list)
    """
    path = _SCHEMA_DIR / "domains.json"
    return _load_json(path)


def get_domain(domain_id: str) -> Optional[Dict[str, Any]]:
    """Vrátí definici konkrétní domény podle id."""
    data = load_domains()
    for dom in data.get("domains", []):
        if dom.get("id") == domain_id:
            return dom
    return None


def list_domain_ids() -> List[str]:
    data = load_domains()
    return [d.get("id") for d in data.get("domains", []) if d.get("id")]


def load_intent(domain_id: str, intent_id: str) -> Optional[Dict[str, Any]]:
    """Načte konkrétní intent JSON podle domény a intent_id."""
    path = _INTENTS_DIR / domain_id / f"{intent_id}.json"
    if not path.exists():
        return None
    return _load_json(path)


def list_intents(domain_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Vrátí seznam všech intentů (nebo jen pro jednu doménu)."""
    intents: List[Dict[str, Any]] = []

    if domain_id:
        domain_path = _INTENTS_DIR / domain_id
        if not domain_path.exists():
            return []
        for p in sorted(domain_path.glob("*.json")):
            data = _load_json(p)
            data.setdefault("_file", str(p.relative_to(_DATA_DIR)))
            intents.append(data)
        return intents

    # všechno
    for domain_path in sorted(_INTENTS_DIR.iterdir()):
        if not domain_path.is_dir():
            continue
        if domain_path.name.startswith("_"):
            continue
        for p in sorted(domain_path.glob("*.json")):
            data = _load_json(p)
            data.setdefault("_file", str(p.relative_to(_DATA_DIR)))
            intents.append(data)
    return intents