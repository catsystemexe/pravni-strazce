#!/usr/bin/env python
from __future__ import annotations

from pathlib import Path

# Natvrdo seznam domén – přesně podle toho, co chceš mít v data/intents/<domain>/
DOMAINS = [
    "school_law",
    "debt_law",
    "environmental_law",
    "property_construction_law",
    "social_law",
    "media_ip_law",
    "constitutional_law",
    "family_law",
    "data_digital_law",
    "labor_law",
    "health_law",
    "tax_law",
    "administrative_law",
    "inheritance_law",
    "criminal_law",
    "traffic_law",
    "corporate_law",
    "civil_law",
    "consumer_finance_law",
    "international_law",
]


def ensure_runtime_intent_dirs(base_dir: Path) -> None:
    """
    Idempotentně zajistí existenci:

    - base_dir (typicky data/intents)
    - base_dir/<domain> pro všechny DOMAINS
    - base_dir/<domain>/.keep (prázdný soubor, pokud neexistuje)
    """
    base_dir.mkdir(parents=True, exist_ok=True)

    for domain in DOMAINS:
        domain_dir = base_dir / domain
        domain_dir.mkdir(parents=True, exist_ok=True)

        keep_file = domain_dir / ".keep"
        if not keep_file.exists():
            keep_file.touch()


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    base_dir = repo_root / "data" / "intents"

    ensure_runtime_intent_dirs(base_dir)

    print(f"[fix_create_intent_runtime_dirs] Ensured runtime dirs in: {base_dir}")
    for domain in DOMAINS:
        print(f"  - {domain}")


if __name__ == "__main__":
    main()
