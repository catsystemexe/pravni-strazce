# tools/generate_intents_from_domains.py
# tools/generate_intents_from_domains.py
from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, List

BASE_SRC_DIR = os.path.join("data", "_source", "domains")   # NOVÁ CESTA


def load_domain_yaml(domain: str, base_src_dir: str = BASE_SRC_DIR) -> Dict[str, Any]:
    """
    Načte hlavní YAML pro danou doménu.
    Očekává soubor data/_source/domains/<domain>/domain.yaml
    """
    yaml_path = os.path.join(base_src_dir, domain, "domain.yaml")
    if not os.path.exists(yaml_path):
        raise FileNotFoundError(f"YAML pro doménu '{domain}' neexistuje: {yaml_path}")

    import yaml  # type: ignore
    with open(yaml_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_subdomains_yaml(domain: str, base_src_dir: str = BASE_SRC_DIR) -> Dict[str, Any]:
    """
    Volitelné subdomény – data/_source/domains/<domain>/subdomains.yaml
    """
    yaml_path = os.path.join(base_src_dir, domain, "subdomains.yaml")
    if not os.path.exists(yaml_path):
        return {}

    import yaml  # type: ignore
    with open(yaml_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def generate_intents_for_domain(
    domain: str,
    base_data_dir: str = DATA_ROOT,
    base_src_dir: str = DOMAINS_SRC_DIR,
) -> List[str]:
    """
    Vygeneruje JSON intents pro danou doménu.

    - načte YAML: base_src_dir/<domain>.yaml
    - vezme pole `intents`
    - pro každý intent vytvoří JSON v:
        base_data_dir/<domain>/<intent_id>.json

    Vrací seznam cest k vytvořeným JSON souborům.
    """
    data = load_domain_yaml(domain, base_src_dir=base_src_dir)

    intents = data.get("intents", [])
    if not isinstance(intents, list):
        raise ValueError("V YAML domény musí být pole 'intents' jako list objektů.")

    out_dir = os.path.join(base_data_dir, domain)
    os.makedirs(out_dir, exist_ok=True)

    written_paths: List[str] = []

    for intent in intents:
        if not isinstance(intent, dict):
            raise ValueError("Každý intent v poli 'intents' musí být objekt (dict).")

        intent_id = intent.get("intent_id")
        if not intent_id:
            raise ValueError("Každý intent musí mít pole 'intent_id'.")

        # Doplníme domain, pokud chybí
        intent.setdefault("domain", domain)

        out_path = os.path.join(out_dir, f"{intent_id}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(intent, f, ensure_ascii=False, indent=2)

        written_paths.append(out_path)

    return written_paths


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Generátor intent JSONů z doménových YAML souborů."
    )
    parser.add_argument(
        "--domain",
        required=True,
        help="ID domény (např. 'traffic_law', 'criminal_law'...).",
    )
    args = parser.parse_args(argv)

    written = generate_intents_for_domain(args.domain)

    print(f"== Generování intentů pro doménu '{args.domain}' ==")
    print(f"Vytvořeno {len(written)} souborů:")
    for p in written:
        print(f" - {p}")


if __name__ == "__main__":
    main()
