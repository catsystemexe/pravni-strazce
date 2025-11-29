# tests/test_generate_intents_from_yaml.py
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.generate_intents_from_yaml import generate_from_yaml
from engines.intent.definition import IntentDefinition


def test_generator_requires_domain_when_not_in_intent(tmp_path: Path) -> None:
    """
    Když YAML nemá ani globální 'domain', ani per-intent 'domain',
    generátor musí spadnout s ValueError.
    """
    yaml_content = """
intents:
  - intent_id: test_intent
    label_cs: "Test intent bez domeny"
    keywords: ["test"]
    negative_keywords: []
"""
    yaml_path = tmp_path / "no_domain.yaml"
    yaml_path.write_text(yaml_content, encoding="utf-8")

    with pytest.raises(ValueError):
        generate_from_yaml(str(yaml_path), output_base=str(tmp_path / "out"))


def test_generator_creates_valid_intent_json(tmp_path: Path) -> None:
    """
    Základní integrační test: z jednoduchého YAML vznikne 1 JSON,
    který úspěšně projde přes IntentDefinition.
    """
    yaml_content = """
domain: traffic_law
intents:
  - intent_id: traffic_speed_offense
    label_cs: "Správní řízení – překročení rychlosti"
    description_cs: "Testovací popis."
    subdomains:
      - spravni_rizeni
    keywords:
      - "rychlost"
      - "radar"
    negative_keywords:
      - "dědictví"
"""
    yaml_path = tmp_path / "traffic_law.yaml"
    yaml_path.write_text(yaml_content, encoding="utf-8")

    out_dir = tmp_path / "out"
    generated_paths = generate_from_yaml(str(yaml_path), output_base=str(out_dir))

    # musí být vygenerován přesně jeden JSON
    assert len(generated_paths) == 1
    json_path = Path(generated_paths[0])
    assert json_path.is_file()

    data = json.loads(json_path.read_text(encoding="utf-8"))

    # základní pole
    assert data["intent_id"] == "traffic_speed_offense"
    assert data["domain"] == "traffic_law"
    assert "keywords" in data
    assert data["keywords"]  # aspoň něco

    # validace přes dataclass – stejná logika jako validate_intents
    IntentDefinition(**data)