# tools/generate_intents_from_yaml.py
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List

import yaml  # používáme stejnou knihovnu jako config_loader
from engines.intent.definition import IntentDefinition


DEFAULT_OUTPUT_BASE = os.path.join("data", "intents")


def _normalize_intent(
    raw_intent: Dict[str, Any],
    default_domain: str | None,
) -> Dict[str, Any]:
    """
    Vezme jeden intent z YAML a převede ho na dict kompatibilní s IntentDefinition.

    - Vyžaduje: intent_id, domain (buď v intentu, nebo default_domain)
    - keywords / negative_keywords doplní na [] pokud chybí
    - Ignoruje pole, která IntentDefinition nezná (např. examples, intent_group)
    - Pro jistotu validuje vytvořený dict přes IntentDefinition(**...)
    """

    intent_id = raw_intent.get("intent_id")
    if not intent_id:
        raise ValueError("Intent v YAML nemá pole 'intent_id'.")

    # domain = per-intent override nebo default z hlavičky
    domain = raw_intent.get("domain") or default_domain
    if not domain:
        raise ValueError(
            f"Intent '{intent_id}' nemá nastavené 'domain' ani v YAML hlavičce."
        )

    out: Dict[str, Any] = {
        "intent_id": intent_id,
        "label_cs": raw_intent.get("label_cs", ""),
        "description_cs": raw_intent.get("description_cs", ""),
        "domain": domain,
        "subdomains": raw_intent.get("subdomains", []),
        "keywords": raw_intent.get("keywords") or [],
        "negative_keywords": raw_intent.get("negative_keywords") or [],
        "risk_patterns": raw_intent.get("risk_patterns", []),
        "basic_questions": raw_intent.get("basic_questions", []),
        "safety_questions": raw_intent.get("safety_questions", []),
        "normative_references": raw_intent.get("normative_references", []),
        "conclusion_skeletons": raw_intent.get("conclusion_skeletons", {}),
        "notes": raw_intent.get("notes", ""),
        "version": raw_intent.get("version", "1.0.0"),
    }

    # POZOR: YAML může mít další pole (examples, intent_group, ...),
    # ale ta schválně do JSONu nedáváme, protože IntentDefinition je nezná
    # a validate_intents by na nich spadnul.

    # Rychlá validace – když to projde tady, projde i validate_intents
    IntentDefinition(**out)

    return out


def generate_from_yaml(
    yaml_path: str,
    output_base: str = DEFAULT_OUTPUT_BASE,
) -> List[str]:
    """
    Načte YAML se seznamem intentů a vygeneruje JSON soubory do data/intents/<domain>.

    YAML může mít jednu z forem:

    1) "doménová" varianta:
        domain: traffic_law
        intents:
          - intent_id: ...
            label_cs: ...
            ...

    2) Seznam intentů, kde každý má vlastní 'domain':
        - intent_id: ...
          domain: traffic_law
          ...

    Vrací seznam cest k vygenerovaným JSON souborům.
    """
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    default_domain: str | None = None
    intents_raw: List[Dict[str, Any]]

    if isinstance(data, dict):
        # doménová varianta
        default_domain = data.get("domain")
        intents_raw = data.get("intents") or []
        if not isinstance(intents_raw, list):
            raise ValueError("V YAML se očekává pole 'intents' jako list.")
    elif isinstance(data, list):
        # čistý seznam intentů, každý musí mít vlastní domain
        intents_raw = data
    else:
        raise ValueError("Neočekávaný formát YAML – musí být dict nebo list.")

    if not intents_raw:
        raise ValueError("YAML neobsahuje žádné intent definice.")

    generated_paths: List[str] = []

    for raw_intent in intents_raw:
        normalized = _normalize_intent(raw_intent, default_domain)
        domain = normalized["domain"]
        intent_id = normalized["intent_id"]

        target_dir = os.path.join(output_base, domain)
        os.makedirs(target_dir, exist_ok=True)

        target_path = os.path.join(target_dir, f"{intent_id}.json")
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(normalized, f, ensure_ascii=False, indent=2)

        generated_paths.append(target_path)
        print(f"[generate_intents] wrote {target_path}")

    return generated_paths


def main(argv: List[str] | None = None) -> int:
    """
    CLI vstup: python -m tools.generate_intents_from_yaml path/to/file.yaml
    """
    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        print("Použití: python -m tools.generate_intents_from_yaml <yaml_path>")
        return 1

    yaml_path = argv[0]
    try:
        generated = generate_from_yaml(yaml_path)
    except Exception as e:
        print(f"[ERROR] Generování intentů selhalo: {e}")
        return 1

    print("== Shrnutí ==")
    print(f"Vygenerováno souborů: {len(generated)}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())