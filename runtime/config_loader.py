"""
Jednoduchý loader YAML konfigurací.

Cíl: mít jedno místo, kde se řeší cesty, chyby, defaulty.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import yaml


BASE_DIR = Path(__file__).resolve().parent.parent


def load_yaml(relative_path: str) -> Dict[str, Any]:
    """
    Načte YAML relativně ke kořeni projektu (BASE_DIR).
    Např.: load_yaml("product/e_advokat_pro/product.yaml")
    """
    full_path = BASE_DIR / relative_path
    if not full_path.exists():
        raise FileNotFoundError(f"Config file not found: {full_path}")
    with open(full_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
