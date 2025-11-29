from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class IntentDefinition:
    intent_id: str
    label_cs: str
    domain: str
    description_cs: str
    subdomains: List[str]
    keywords: List[str]
    negative_keywords: List[str]
    risk_patterns: List[Dict[str, Any]]
    basic_questions: List[str]
    safety_questions: List[str]
    normative_references: List[str]
    conclusion_skeletons: Dict[str, str]

    # volitelné / doplňkové věci musí být na konci (mají defaulty)
    notes: str = ""
    version: str = "1.0.0"
    intent_group: str = "general"
    examples: List[str] = field(default_factory=list)